"""
Tactical Deliberation Manager
Manages MDMP-based tactical deliberation using knowledge graph entities
and AI staff officer agents.
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .zep_entity_reader import ZepEntityReader, FilteredEntities
from .tactical_agent_generator import TacticalAgentGenerator, TacticalAgentProfile
from .deliberation_config_generator import DeliberationConfigGenerator, DeliberationParameters

logger = get_logger('mirofish.simulation')


class SimulationStatus(str, Enum):
    """Simulation status"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SimulationState:
    """Deliberation state"""
    simulation_id: str
    project_id: str
    graph_id: str

    # Status
    status: SimulationStatus = SimulationStatus.CREATED

    # Preparation data
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)

    # Config generation
    config_generated: bool = False
    config_reasoning: str = ""

    # Phase tracking
    current_phase: int = 0
    current_phase_name: str = ""
    total_phases: int = 7
    current_round: int = 0
    coas_proposed: int = 0
    deliberation_status: str = "not_started"

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Error info
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Full state dict (internal use)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_phase": self.current_phase,
            "current_phase_name": self.current_phase_name,
            "total_phases": self.total_phases,
            "current_round": self.current_round,
            "coas_proposed": self.coas_proposed,
            "deliberation_status": self.deliberation_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """Simplified state dict (API response)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """
    模拟管理器
    
    Core functions:
    1. Read entities from Zep graph
    2. Generate tactical staff officer agent profiles
    3. Generate deliberation configuration using LLM
    4. Prepare all files for deliberation script
    """
    
    # 模拟数据存储目录
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__), 
        '../../uploads/simulations'
    )
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        
        # 内存中的模拟状态缓存
        self._simulations: Dict[str, SimulationState] = {}
    
    def _get_simulation_dir(self, simulation_id: str) -> str:
        """获取模拟数据目录"""
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """保存模拟状态到文件"""
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        state.updated_at = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """从文件加载模拟状态"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_phase=data.get("current_phase", 0),
            current_phase_name=data.get("current_phase_name", ""),
            total_phases=data.get("total_phases", 7),
            current_round=data.get("current_round", 0),
            coas_proposed=data.get("coas_proposed", 0),
            deliberation_status=data.get("deliberation_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )
        
        self._simulations[simulation_id] = state
        return state
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        **kwargs,
    ) -> SimulationState:
        """
        Create a new deliberation.

        Args:
            project_id: Project ID
            graph_id: Zep graph ID

        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            status=SimulationStatus.CREATED,
        )

        self._save_simulation_state(state)
        logger.info(f"Created deliberation: {simulation_id}, project={project_id}, graph={graph_id}")

        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3
    ) -> SimulationState:
        """
        Prepare deliberation environment (fully automated).

        Steps:
        1. Read and filter entities from Zep graph
        2. Generate tactical staff officer agent profiles
        3. Generate deliberation configuration (phases, criteria, mission config)
        4. Save config and agent files
        
        Args:
            simulation_id: 模拟ID
            simulation_requirement: 模拟需求描述（用于LLM生成配置）
            document_text: 原始文档内容（用于LLM理解背景）
            defined_entity_types: 预定义的实体类型（可选）
            use_llm_for_profiles: 是否使用LLM生成详细人设
            progress_callback: 进度回调函数 (stage, progress, message)
            parallel_profile_count: 并行生成人设的数量，默认3
            
        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"模拟不存在: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== 阶段1: 读取并过滤实体 ==========
            if progress_callback:
                progress_callback("reading", 0, "正在连接Zep图谱...")
            
            reader = ZepEntityReader()
            
            if progress_callback:
                progress_callback("reading", 30, "正在读取节点数据...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"完成，共 {filtered.filtered_count} 个实体",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "没有找到符合条件的实体，请检查图谱是否正确构建"
                self._save_simulation_state(state)
                return state
            
            # ========== Stage 2: Generate Tactical Staff Agents ==========
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0,
                    "Generating tactical staff agents...",
                    current=0,
                    total=10
                )

            agent_generator = TacticalAgentGenerator()

            def agent_progress(pct, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles",
                        pct,
                        msg,
                        current=int(pct / 10),
                        total=10,
                        item_name=msg
                    )

            agents = agent_generator.generate_all_agents(
                graph_id=state.graph_id,
                mission_context=simulation_requirement,
                use_llm=use_llm_for_profiles,
                entity_types=defined_entity_types,
                progress_callback=agent_progress,
            )

            state.profiles_count = len(agents)

            # Save agents to JSON
            agents_path = os.path.join(sim_dir, "agents.json")
            TacticalAgentGenerator.save_agents_json(agents, agents_path)

            if progress_callback:
                progress_callback(
                    "generating_profiles", 100,
                    f"Generated {len(agents)} tactical staff agents",
                    current=len(agents),
                    total=len(agents)
                )
            
            # ========== Stage 3: Generate Deliberation Configuration ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0,
                    "Analyzing mission requirements...",
                    current=0,
                    total=3
                )

            config_generator = DeliberationConfigGenerator()

            def config_progress(pct, msg):
                if progress_callback:
                    progress_callback(
                        "generating_config",
                        pct,
                        msg,
                        current=max(1, pct // 33),
                        total=3
                    )

            delib_params = config_generator.generate_full_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                document_text=document_text,
                analysis_requirement=simulation_requirement,
                progress_callback=config_progress,
            )

            # Save config
            config_path = os.path.join(sim_dir, "deliberation_config.json")
            DeliberationConfigGenerator.save_config(delib_params, config_path)

            # Also save as simulation_config.json for backward compatibility
            compat_path = os.path.join(sim_dir, "simulation_config.json")
            DeliberationConfigGenerator.save_config(delib_params, compat_path)

            state.config_generated = True
            state.config_reasoning = f"Mission type: {delib_params.mission_config.mission_type}, Urgency: {delib_params.mission_config.urgency}"
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "配置生成完成",
                    current=3,
                    total=3
                )
            
            # 注意：运行脚本保留在 backend/scripts/ 目录，不再复制到模拟目录
            # 启动模拟时，simulation_runner 会从 scripts/ 目录运行脚本
            
            # 更新状态
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"模拟准备完成: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"模拟准备失败: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """获取模拟状态"""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """列出所有模拟"""
        simulations = []
        
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # 跳过隐藏文件（如 .DS_Store）和非目录文件
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "tactical") -> List[Dict[str, Any]]:
        """Get tactical agent profiles."""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        sim_dir = self._get_simulation_dir(simulation_id)

        # Try new agents.json first, fall back to legacy formats
        agents_path = os.path.join(sim_dir, "agents.json")
        if os.path.exists(agents_path):
            with open(agents_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("agents", [])

        # Legacy fallback
        legacy_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        if os.path.exists(legacy_path):
            with open(legacy_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return []
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """获取模拟配置"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Get run instructions for the deliberation."""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "deliberation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        graph_id = ""
        state = self._load_simulation_state(simulation_id)
        if state:
            graph_id = state.graph_id

        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "deliberation": f"python {scripts_dir}/run_tactical_deliberation.py --simulation-dir {sim_dir} --graph-id {graph_id}",
            },
            "instructions": (
                f"1. Activate environment: conda activate MiroFish\n"
                f"2. Run deliberation:\n"
                f"   python {scripts_dir}/run_tactical_deliberation.py --simulation-dir {sim_dir} --graph-id {graph_id}"
            )
        }
