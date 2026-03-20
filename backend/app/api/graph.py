"""
Graph-related API routes
Uses project context mechanism with server-side persistent state
"""

import os
import traceback
import threading
from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get logger
logger = get_logger('mirofish.api')


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project Management Endpoints ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """
    Get project details
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """
    List all projects
    """
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """
    Delete project
    """
    success = ProjectManager.delete_project(project_id)
    
    if not success:
        return jsonify({
            "success": False,
            "error": f"Project not found or deletion failed: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """
    Reset project status (for rebuilding graph)
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404
    
    # Reset to ontology-generated status
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED
    
    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)
    
    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Endpoint 1: Upload Files and Generate Ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    Endpoint 1: Upload files and generate ontology definition
    
    Request: multipart/form-data
    
    Parameters:
        files: Upload files (PDF/MD/TXT), multiple allowed
        simulation_requirement: Simulation requirement description (required)
        project_name: Project name (optional)
        additional_context: Additional notes (optional)
        
    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== Starting ontology generation ===")
        
        # Get parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        domain_hints = request.form.get('domain_hints', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')

        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Simulation requirement: {simulation_requirement[:100] if simulation_requirement else '(none)'}...")
        logger.debug(f"Domain hints: {domain_hints[:100] if domain_hints else '(none)'}...")
        
        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload at least one document file"
            }), 400
        
        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement if simulation_requirement else None
        project.domain_hints = domain_hints if domain_hints else None
        logger.info(f"Created project: {project.project_id}")
        
        # Save files and extract text
        document_texts = []
        all_text = ""
        
        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Save file to project directory
                file_info = ProjectManager.save_file_to_project(
                    project.project_id, 
                    file, 
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })
                
                # Extract text
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
        
        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "Failed to process any documents, please check file format"
            }), 400
        
        # Save extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction complete, {len(all_text)} characters total")
        
        # Generate ontology
        logger.info("Calling LLM to generate ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement if simulation_requirement else None,
            additional_context=additional_context if additional_context else None,
            domain_hints=domain_hints if domain_hints else None
        )
        
        # Save ontology to project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generation complete: {entity_count} entity types, {edge_count} relationship types")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", []),
            "role_assignments": ontology.get("role_assignments"),
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation complete === project_id: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Endpoint 2: Build Graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    Endpoint 2: Build graph from project_id
    
    Request (JSON):
        {
            "project_id": "proj_xxxx",  // required, from endpoint 1
            "graph_name": "Graph Name",  // optional
            "chunk_size": 500,          // optional, default 500
            "chunk_overlap": 50         // optional, default 50
        }
        
    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph build task started"
            }
        }
    """
    try:
        logger.info("=== Starting graph build ===")
        
        # Check configuration
        errors = []
        if not Config.NEO4J_URI:
            errors.append("NEO4J_URI not configured")
        if errors:
            logger.error(f"Configuration error: {errors}")
            return jsonify({
                "success": False,
                "error": "Configuration error: " + "; ".join(errors)
            }), 500
        
        # Parse request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request params: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400
        
        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project not found: {project_id}"
            }), 404
        
        # Check project status
        force = data.get('force', False)  # Force rebuild
        
        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "Project ontology not yet generated, please call /ontology/generate first"
            }), 400
        
        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "Graph is currently being built. To force rebuild, add force: true",
                "task_id": project.graph_build_task_id
            }), 400
        
        # If force rebuild, reset status
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None
        
        # Get configuration
        graph_name = data.get('graph_name', project.name or 'MiroFish Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)
        
        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap
        
        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "Extracted text content not found"
            }), 400
        
        # Get ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "Ontology definition not found"
            }), 400
        
        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Created graph build task: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)
        
        # Start background task
        def build_task():
            build_logger = get_logger('mirofish.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(
                    task_id, 
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph build service..."
                )
                
                # Create graph build service
                builder = GraphBuilderService()
                
                # Chunking
                task_manager.update_task(
                    task_id,
                    message="Chunking text...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text, 
                    chunk_size=chunk_size, 
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)
                
                # Create graph
                task_manager.update_task(
                    task_id,
                    message="Creating graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)
                
                # Update project graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)
                
                # Set ontology
                task_manager.update_task(
                    task_id,
                    message="Setting ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (progress_callback signature is (msg, progress_ratio))
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 75)  # 15% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )
                
                task_manager.update_task(
                    task_id,
                    message=f"Adding {total_chunks} text chunks...",
                    progress=15
                )
                
                builder.add_text_batches(
                    graph_id,
                    chunks,
                    batch_size=Config.GRAPH_BUILD_BATCH_SIZE,
                    progress_callback=add_progress_callback
                )

                # Get graph data
                task_manager.update_task(
                    task_id,
                    message="Retrieving graph data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)
                
                # Update project status + graph library metadata
                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                project.status = ProjectStatus.GRAPH_COMPLETED
                project.node_count = node_count
                project.edge_count = edge_count
                project.graph_name = project.graph_name or graph_name
                # Extract entity type names from ontology
                if project.ontology and "entity_types" in project.ontology:
                    project.entity_types_list = [
                        et["name"] for et in project.ontology["entity_types"]
                    ]
                ProjectManager.save_project(project)
                build_logger.info(f"[{task_id}] Graph build complete: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")
                
                # Complete
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph build complete",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )
                
            except Exception as e:
                # Update project status to failed
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())
                
                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)
                
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=traceback.format_exc()
                )
        
        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph build task started. Query progress via /task/{task_id}"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Task Query Endpoints ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """
    Query task status
    """
    task = TaskManager().get_task(task_id)
    
    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """
    List all tasks
    """
    tasks = TaskManager().list_tasks()
    
    return jsonify({
        "success": True,
        "data": [t.to_dict() for t in tasks],
        "count": len(tasks)
    })


# ============== Graph Data Endpoints ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    try:
        if not Config.NEO4J_URI:
            return jsonify({
                "success": False,
                "error": "NEO4J_URI not configured"
            }), 500
        
        builder = GraphBuilderService()
        graph_data = builder.get_graph_data(graph_id)
        
        return jsonify({
            "success": True,
            "data": graph_data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """
    Delete Zep graph
    """
    try:
        if not Config.NEO4J_URI:
            return jsonify({
                "success": False,
                "error": "NEO4J_URI not configured"
            }), 500
        
        builder = GraphBuilderService()
        builder.delete_graph(graph_id)

        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Graph Library API ==============

@graph_bp.route('/library', methods=['GET'])
def get_graph_library():
    """
    List all completed graphs as reusable knowledge graph assets.
    Returns projects with status >= GRAPH_COMPLETED, enriched with graph metadata.
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        projects = ProjectManager.list_projects(limit=limit)

        graphs = []
        for p in projects:
            if p.status not in (ProjectStatus.GRAPH_COMPLETED,) or not p.graph_id:
                continue
            graphs.append({
                "graph_id": p.graph_id,
                "project_id": p.project_id,
                "name": p.graph_name or p.name,
                "description": p.graph_description or p.analysis_summary or "",
                "tags": p.graph_tags,
                "documents": p.files,
                "node_count": p.node_count,
                "edge_count": p.edge_count,
                "entity_types": p.entity_types_list,
                "deliberation_count": p.deliberation_count,
                "simulation_requirement": p.simulation_requirement,
                "domain_hints": p.domain_hints,
                "created_at": p.created_at,
                "last_queried_at": p.last_queried_at,
            })

        return jsonify({
            "success": True,
            "data": graphs,
            "count": len(graphs)
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/library/<graph_id>', methods=['GET'])
def get_graph_detail(graph_id: str):
    """
    Get detailed info for a single graph, including its deliberation history.
    """
    try:
        # Find the project that owns this graph
        projects = ProjectManager.list_projects(limit=500)
        project = next((p for p in projects if p.graph_id == graph_id), None)

        if not project:
            return jsonify({"success": False, "error": f"Graph not found: {graph_id}"}), 404

        # Get associated simulations
        from ..services.simulation_manager import SimulationManager
        manager = SimulationManager()
        simulations = manager.list_simulations(project_id=project.project_id)

        sim_list = []
        for s in simulations:
            sim_data = s.to_simple_dict()
            sim_data["mission_objective"] = getattr(s, "mission_objective", "") or project.simulation_requirement or ""
            sim_list.append(sim_data)

        return jsonify({
            "success": True,
            "data": {
                "graph_id": graph_id,
                "project_id": project.project_id,
                "name": project.graph_name or project.name,
                "description": project.graph_description or project.analysis_summary or "",
                "tags": project.graph_tags,
                "documents": project.files,
                "node_count": project.node_count,
                "edge_count": project.edge_count,
                "entity_types": project.entity_types_list,
                "ontology": project.ontology,
                "simulation_requirement": project.simulation_requirement,
                "domain_hints": project.domain_hints,
                "created_at": project.created_at,
                "deliberations": sim_list,
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/library/<graph_id>', methods=['PATCH'])
def update_graph_meta(graph_id: str):
    """
    Update graph metadata (name, description, tags).
    """
    try:
        projects = ProjectManager.list_projects(limit=500)
        project = next((p for p in projects if p.graph_id == graph_id), None)

        if not project:
            return jsonify({"success": False, "error": f"Graph not found: {graph_id}"}), 404

        data = request.get_json() or {}

        if "name" in data:
            project.graph_name = data["name"]
        if "description" in data:
            project.graph_description = data["description"]
        if "tags" in data:
            project.graph_tags = data["tags"]

        ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "message": f"Graph metadata updated: {graph_id}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/library/<graph_id>', methods=['DELETE'])
def delete_graph_from_library(graph_id: str):
    """
    Delete a graph from Neo4j and its associated project.
    """
    try:
        projects = ProjectManager.list_projects(limit=500)
        project = next((p for p in projects if p.graph_id == graph_id), None)

        if not project:
            return jsonify({"success": False, "error": f"Graph not found: {graph_id}"}), 404

        # Delete from Neo4j
        builder = GraphBuilderService()
        builder.delete_graph(graph_id)

        # Delete project files
        ProjectManager.delete_project(project.project_id)

        return jsonify({
            "success": True,
            "message": f"Graph and project deleted: {graph_id}"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@graph_bp.route('/library/<graph_id>/deliberate', methods=['POST'])
def deliberate_on_graph(graph_id: str):
    """
    Start a new deliberation on an existing graph.
    Creates a simulation with a new mission_objective without rebuilding the graph.

    Request (JSON):
        {
            "mission_objective": "What is the best route of advance?",
            "max_rounds": 25  // optional
        }

    Returns:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "graph_id": "mirofish_xxxx",
                "project_id": "proj_xxxx",
                "mission_objective": "..."
            }
        }
    """
    try:
        # Find the project that owns this graph
        projects = ProjectManager.list_projects(limit=500)
        project = next((p for p in projects if p.graph_id == graph_id), None)

        if not project:
            return jsonify({"success": False, "error": f"Graph not found: {graph_id}"}), 404

        data = request.get_json() or {}
        mission_objective = data.get("mission_objective", "").strip()

        if not mission_objective:
            return jsonify({
                "success": False,
                "error": "mission_objective is required"
            }), 400

        # Create simulation with the new mission objective
        from ..services.simulation_manager import SimulationManager
        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project.project_id,
            graph_id=graph_id,
        )

        # Store mission_objective on the simulation state
        state.mission_objective = mission_objective
        manager._save_simulation_state(state)

        # Update graph library stats
        project.deliberation_count += 1
        from datetime import datetime as dt
        project.last_queried_at = dt.now().isoformat()
        ProjectManager.save_project(project)

        logger.info(f"New deliberation on graph {graph_id}: sim={state.simulation_id}, objective={mission_objective[:80]}")

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": state.simulation_id,
                "graph_id": graph_id,
                "project_id": project.project_id,
                "mission_objective": mission_objective,
            }
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
