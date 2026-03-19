"""
Graph builder service — builds knowledge graphs using Graphiti + Neo4j.
"""

import uuid
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType, EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.graphiti import RawEpisode

from ..config import Config
from ..utils.graphiti_client import get_graphiti, run_async
from ..models.task import TaskManager, TaskStatus
from ..utils.graph_paging import fetch_all_nodes, fetch_all_edges
from .text_processor import TextProcessor


@dataclass
class GraphInfo:
    """Graph info summary"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Graph builder service — uses Graphiti to build knowledge graphs.
    """

    def __init__(self):
        self.graphiti = get_graphiti()
        self.task_manager = TaskManager()
        # Ontology stored for per-episode use
        self._entity_types: Dict[str, type] = {}
        self._edge_types: Dict[str, type] = {}
        self._edge_type_map: Dict[tuple, list] = {}

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """Start graph building in a background thread. Returns task_id."""
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )

        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size)
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int
    ):
        """Graph build worker thread — runs its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._async_build_graph(task_id, text, ontology, graph_name,
                                         chunk_size, chunk_overlap, batch_size)
            )
        finally:
            loop.close()

    async def _async_build_graph(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int
    ):
        """Async graph build implementation."""
        try:
            self.task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING, progress=5,
                message="Starting graph build..."
            )

            # 1. Create graph (just generate group_id — graph exists implicitly)
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id, progress=10,
                message=f"Graph created: {graph_id}"
            )

            # 2. Set ontology (stores Pydantic models for per-episode use)
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id, progress=15, message="Ontology configured"
            )

            # 3. Split text into chunks
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id, progress=20,
                message=f"Text split into {total_chunks} chunks"
            )

            # 4. Add episodes (Graphiti processes synchronously — no polling needed)
            for i in range(0, total_chunks, batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_chunks + batch_size - 1) // batch_size

                progress_pct = 20 + int(((i + len(batch_chunks)) / total_chunks) * 70)
                self.task_manager.update_task(
                    task_id, progress=progress_pct,
                    message=f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)..."
                )

                for chunk in batch_chunks:
                    await self.graphiti.add_episode(
                        name=f"{graph_id}_chunk_{i}",
                        episode_body=chunk,
                        source=EpisodeType.text,
                        source_description=f"Document chunk for graph {graph_id}",
                        reference_time=datetime.now(timezone.utc),
                        group_id=graph_id,
                        entity_types=self._entity_types if self._entity_types else None,
                        edge_types=self._edge_types if self._edge_types else None,
                        edge_type_map=self._edge_type_map if self._edge_type_map else None,
                    )

                # Brief pause between batches
                await asyncio.sleep(0.5)

            # 5. Get graph info
            self.task_manager.update_task(
                task_id, progress=90, message="Retrieving graph data..."
            )

            graph_info = self._get_graph_info(graph_id)

            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """Create a new graph (generates a group_id — graph exists implicitly in Graphiti)."""
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Convert ontology definition to Graphiti-compatible Pydantic models.

        Unlike Zep Cloud (which sets ontology globally on a graph), Graphiti
        receives entity_types/edge_types per add_episode() call. We store
        the converted models as instance attributes.
        """
        # Protected names that cannot be used as attribute names
        RESERVED_NAMES = {'uuid', 'name', 'group_id', 'name_embedding', 'summary',
                          'created_at', 'labels', 'attributes'}

        def safe_attr_name(attr_name: str) -> str:
            if attr_name.lower() in RESERVED_NAMES:
                return f"entity_{attr_name}"
            return attr_name

        # Build entity types as standard Pydantic BaseModel classes
        entity_types = {}
        for entity_def in ontology.get("entity_types", []):
            ename = entity_def["name"]
            description = entity_def.get("description", f"A {ename} entity.")

            attrs: Dict[str, Any] = {"__doc__": description}
            annotations: Dict[str, Any] = {}

            for attr_def in entity_def.get("attributes", []):
                attr_name = safe_attr_name(attr_def["name"])
                attr_desc = attr_def.get("description", attr_name)
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[str]

            attrs["__annotations__"] = annotations
            entity_class = type(ename, (BaseModel,), attrs)
            entity_class.__doc__ = description
            entity_types[ename] = entity_class

        # Build edge types
        edge_types = {}
        edge_type_map: Dict[tuple, list] = {}

        for edge_def in ontology.get("edge_types", []):
            ename = edge_def["name"]
            description = edge_def.get("description", f"A {ename} relationship.")

            attrs = {"__doc__": description}
            annotations = {}

            for attr_def in edge_def.get("attributes", []):
                attr_name = safe_attr_name(attr_def["name"])
                attr_desc = attr_def.get("description", attr_name)
                attrs[attr_name] = Field(description=attr_desc, default=None)
                annotations[attr_name] = Optional[str]

            attrs["__annotations__"] = annotations
            class_name = ''.join(word.capitalize() for word in ename.split('_'))
            edge_class = type(class_name, (BaseModel,), attrs)
            edge_class.__doc__ = description
            edge_types[ename] = edge_class

            # Build edge_type_map from source_targets
            for st in edge_def.get("source_targets", []):
                source = st.get("source", "Entity")
                target = st.get("target", "Entity")
                key = (source, target)
                if key not in edge_type_map:
                    edge_type_map[key] = []
                if ename not in edge_type_map[key]:
                    edge_type_map[key].append(ename)

        self._entity_types = entity_types
        self._edge_types = edge_types
        self._edge_type_map = edge_type_map

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add text chunks as episodes. Returns empty list (no polling needed)."""
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress = (i + 1) / total_chunks
                progress_callback(
                    f"Processing chunk {i + 1}/{total_chunks}...",
                    progress
                )

            run_async(self.graphiti.add_episode(
                name=f"{graph_id}_chunk_{i}",
                episode_body=chunk,
                source=EpisodeType.text,
                source_description=f"Document chunk for graph {graph_id}",
                reference_time=datetime.now(timezone.utc),
                group_id=graph_id,
                entity_types=self._entity_types if self._entity_types else None,
                edge_types=self._edge_types if self._edge_types else None,
                edge_type_map=self._edge_type_map if self._edge_type_map else None,
            ))

            time.sleep(0.5)

        return []  # No episode UUIDs to poll — processing is synchronous

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get graph summary info."""
        nodes = fetch_all_nodes(self.graphiti, graph_id)
        edges = fetch_all_edges(self.graphiti, graph_id)

        entity_types = set()
        for node in nodes:
            if node.labels:
                for label in node.labels:
                    if label not in ["Entity", "Node"]:
                        entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types)
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Get complete graph data with nodes and edges."""
        nodes = fetch_all_nodes(self.graphiti, graph_id)
        edges = fetch_all_edges(self.graphiti, graph_id)

        node_map = {}
        for node in nodes:
            node_map[node.uuid] = node.name or ""

        nodes_data = []
        for node in nodes:
            created_at = getattr(node, 'created_at', None)
            if created_at:
                created_at = str(created_at)

            nodes_data.append({
                "uuid": node.uuid,
                "name": node.name,
                "labels": node.labels or [],
                "summary": node.summary or "",
                "attributes": node.attributes or {},
                "created_at": created_at,
            })

        edges_data = []
        for edge in edges:
            created_at = getattr(edge, 'created_at', None)
            valid_at = getattr(edge, 'valid_at', None)
            invalid_at = getattr(edge, 'invalid_at', None)
            expired_at = getattr(edge, 'expired_at', None)
            episodes = getattr(edge, 'episodes', None) or []
            if episodes and not isinstance(episodes, list):
                episodes = [str(episodes)]
            else:
                episodes = [str(e) for e in episodes]

            edges_data.append({
                "uuid": edge.uuid,
                "name": edge.name or "",
                "fact": edge.fact or "",
                "fact_type": edge.name or "",
                "source_node_uuid": edge.source_node_uuid,
                "target_node_uuid": edge.target_node_uuid,
                "source_node_name": node_map.get(edge.source_node_uuid, ""),
                "target_node_name": node_map.get(edge.target_node_uuid, ""),
                "attributes": edge.attributes or {},
                "created_at": str(created_at) if created_at else None,
                "valid_at": str(valid_at) if valid_at else None,
                "invalid_at": str(invalid_at) if invalid_at else None,
                "expired_at": str(expired_at) if expired_at else None,
                "episodes": episodes,
            })

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        """Delete a graph (all data in the group)."""
        run_async(self.graphiti.delete_group(graph_id))
