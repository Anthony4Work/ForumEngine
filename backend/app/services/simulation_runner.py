"""
Tactical Deliberation Runner
Runs MDMP deliberation in background subprocess and monitors agent actions in real-time.
"""

import os
import sys
import json
import time
import asyncio
import threading
import subprocess
import signal
import atexit
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue

from ..config import Config
from ..utils.logger import get_logger
from .zep_graph_memory_updater import ZepGraphMemoryManager
from .simulation_ipc import SimulationIPCClient, CommandType, IPCResponse

logger = get_logger('mirofish.simulation_runner')

# Flag to prevent duplicate cleanup registration
_cleanup_registered = False

# Platform detection
IS_WINDOWS = sys.platform == 'win32'


class RunnerStatus(str, Enum):
    """Runner status"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentAction:
    """Agent action record for tactical deliberation"""
    phase: int
    phase_name: str
    round_num: int
    timestamp: str
    agent_id: int
    agent_name: str
    agent_role: str  # CDR, S2, S3, etc.
    action_type: str  # propose_coa, assess_threat, etc.
    content: str = ""
    references: List[str] = field(default_factory=list)
    confidence: float = 0.0
    risk_assessment: str = ""
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "phase_name": self.phase_name,
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "action_type": self.action_type,
            "content": self.content[:500] if self.content else "",
            "references": self.references,
            "confidence": self.confidence,
            "risk_assessment": self.risk_assessment,
            "success": self.success,
        }


@dataclass
class PhaseRoundSummary:
    """Summary for a deliberation phase"""
    phase: int
    phase_name: str
    start_time: str
    end_time: Optional[str] = None
    rounds_completed: int = 0
    actions_count: int = 0
    active_agents: List[int] = field(default_factory=list)
    actions: List[AgentAction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "phase_name": self.phase_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "rounds_completed": self.rounds_completed,
            "actions_count": self.actions_count,
            "active_agents": self.active_agents,
        }


@dataclass
class SimulationRunState:
    """Real-time deliberation run state"""
    simulation_id: str
    runner_status: RunnerStatus = RunnerStatus.IDLE

    # Phase tracking
    current_phase: int = 0
    current_phase_name: str = ""
    total_phases: int = 7  # MDMP has 7 phases
    phase_round: int = 0

    # Progress
    current_round: int = 0     # Global round counter
    total_rounds: int = 0      # Estimated total rounds across all phases

    # Deliberation metrics
    deliberation_actions_count: int = 0
    coas_proposed: int = 0
    selected_coa: Optional[str] = None

    # Phase summaries
    phases: List[PhaseRoundSummary] = field(default_factory=list)

    # Recent actions (for frontend real-time display)
    recent_actions: List[AgentAction] = field(default_factory=list)
    max_recent_actions: int = 50

    # Timestamps
    started_at: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    # Error info
    error: Optional[str] = None

    # Process PID (for stopping)
    process_pid: Optional[int] = None

    def add_action(self, action: AgentAction):
        """Add action to recent actions list"""
        self.recent_actions.insert(0, action)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[:self.max_recent_actions]

        self.deliberation_actions_count += 1
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "runner_status": self.runner_status.value,
            # Phase tracking
            "current_phase": self.current_phase,
            "current_phase_name": self.current_phase_name,
            "total_phases": self.total_phases,
            "phase_round": self.phase_round,
            # Progress
            "current_round": self.current_round,
            "total_rounds": self.total_rounds,
            "progress_percent": round(self.current_phase / max(self.total_phases, 1) * 100, 1),
            # Deliberation metrics
            "deliberation_actions_count": self.deliberation_actions_count,
            "coas_proposed": self.coas_proposed,
            "selected_coa": self.selected_coa,
            # Timestamps
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "process_pid": self.process_pid,
        }

    def to_detail_dict(self) -> Dict[str, Any]:
        """Detailed info including recent actions"""
        result = self.to_dict()
        result["recent_actions"] = [a.to_dict() for a in self.recent_actions]
        result["phases_completed"] = len(self.phases)
        return result


class SimulationRunner:
    """
    Tactical Deliberation Runner

    Responsibilities:
    1. Run MDMP deliberation in background subprocess
    2. Parse action logs, track each agent's contributions
    3. Provide real-time status queries (phase, round, COAs)
    4. Support stop/pause operations
    """

    # Run state storage directory
    RUN_STATE_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    # Scripts directory
    SCRIPTS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../scripts'
    )

    # In-memory run states
    _run_states: Dict[str, SimulationRunState] = {}
    _processes: Dict[str, subprocess.Popen] = {}
    _action_queues: Dict[str, Queue] = {}
    _monitor_threads: Dict[str, threading.Thread] = {}
    _stdout_files: Dict[str, Any] = {}
    _stderr_files: Dict[str, Any] = {}

    # Graph memory update config
    _graph_memory_enabled: Dict[str, bool] = {}

    @classmethod
    def get_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Get run state"""
        if simulation_id in cls._run_states:
            return cls._run_states[simulation_id]

        # Try loading from file
        state = cls._load_run_state(simulation_id)
        if state:
            cls._run_states[simulation_id] = state
        return state

    @classmethod
    def _load_run_state(cls, simulation_id: str) -> Optional[SimulationRunState]:
        """Load run state from file"""
        state_file = os.path.join(cls.RUN_STATE_DIR, simulation_id, "run_state.json")
        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            state = SimulationRunState(
                simulation_id=simulation_id,
                runner_status=RunnerStatus(data.get("runner_status", "idle")),
                current_phase=data.get("current_phase", 0),
                current_phase_name=data.get("current_phase_name", ""),
                total_phases=data.get("total_phases", 7),
                phase_round=data.get("phase_round", 0),
                current_round=data.get("current_round", 0),
                total_rounds=data.get("total_rounds", 0),
                deliberation_actions_count=data.get("deliberation_actions_count", 0),
                coas_proposed=data.get("coas_proposed", 0),
                selected_coa=data.get("selected_coa"),
                started_at=data.get("started_at"),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                completed_at=data.get("completed_at"),
                error=data.get("error"),
                process_pid=data.get("process_pid"),
            )

            # Load recent actions
            actions_data = data.get("recent_actions", [])
            for a in actions_data:
                state.recent_actions.append(AgentAction(
                    phase=a.get("phase", 0),
                    phase_name=a.get("phase_name", ""),
                    round_num=a.get("round_num", 0),
                    timestamp=a.get("timestamp", ""),
                    agent_id=a.get("agent_id", 0),
                    agent_name=a.get("agent_name", ""),
                    agent_role=a.get("agent_role", ""),
                    action_type=a.get("action_type", ""),
                    content=a.get("content", ""),
                    references=a.get("references", []),
                    confidence=a.get("confidence", 0.0),
                    risk_assessment=a.get("risk_assessment", ""),
                    success=a.get("success", True),
                ))

            return state
        except Exception as e:
            logger.error(f"Failed to load run state: {str(e)}")
            return None

    @classmethod
    def _save_run_state(cls, state: SimulationRunState):
        """Save run state to file"""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, state.simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        state_file = os.path.join(sim_dir, "run_state.json")

        data = state.to_detail_dict()

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        cls._run_states[state.simulation_id] = state

    @classmethod
    def start_simulation(
        cls,
        simulation_id: str,
        platform: str = "deliberation",  # kept for API compat, ignored
        max_rounds: int = None,
        enable_graph_memory_update: bool = False,
        graph_id: str = None
    ) -> SimulationRunState:
        """
        Start tactical deliberation.

        Args:
            simulation_id: Simulation ID
            platform: Ignored (kept for backward compatibility)
            max_rounds: Max deliberation rounds (optional)
            enable_graph_memory_update: Whether to update Zep graph with deliberation activities
            graph_id: Zep graph ID (required if graph memory update enabled)

        Returns:
            SimulationRunState
        """
        # Check if already running
        existing = cls.get_run_state(simulation_id)
        if existing and existing.runner_status in [RunnerStatus.RUNNING, RunnerStatus.STARTING]:
            raise ValueError(f"Deliberation already running: {simulation_id}")

        # Load deliberation config
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)

        # Try deliberation_config.json first, fall back to simulation_config.json
        config_path = os.path.join(sim_dir, "deliberation_config.json")
        if not os.path.exists(config_path):
            config_path = os.path.join(sim_dir, "simulation_config.json")

        if not os.path.exists(config_path):
            raise ValueError(f"Deliberation config not found. Call /prepare first.")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Calculate total rounds from phases
        phases = config.get("phases", [])
        total_rounds = sum(p.get("max_rounds", 3) for p in phases) if phases else 25
        total_phases = len(phases) if phases else 7

        # If graph_id not provided, try to get from config
        if not graph_id:
            graph_id = config.get("graph_id", "")

        state = SimulationRunState(
            simulation_id=simulation_id,
            runner_status=RunnerStatus.STARTING,
            total_rounds=total_rounds,
            total_phases=total_phases,
            started_at=datetime.now().isoformat(),
        )

        cls._save_run_state(state)

        # Enable graph memory update if requested
        if enable_graph_memory_update:
            if not graph_id:
                raise ValueError("graph_id required when graph memory update is enabled")

            try:
                ZepGraphMemoryManager.create_updater(simulation_id, graph_id)
                cls._graph_memory_enabled[simulation_id] = True
                logger.info(f"Graph memory update enabled: simulation_id={simulation_id}, graph_id={graph_id}")
            except Exception as e:
                logger.error(f"Failed to create graph memory updater: {e}")
                cls._graph_memory_enabled[simulation_id] = False
        else:
            cls._graph_memory_enabled[simulation_id] = False

        # Launch deliberation script
        script_name = "run_tactical_deliberation.py"
        script_path = os.path.join(cls.SCRIPTS_DIR, script_name)

        if not os.path.exists(script_path):
            raise ValueError(f"Script not found: {script_path}")

        # Create action queue
        action_queue = Queue()
        cls._action_queues[simulation_id] = action_queue

        # Start subprocess
        try:
            cmd = [
                sys.executable,
                script_path,
                "--simulation-dir", sim_dir,
                "--graph-id", graph_id or "",
            ]

            # Create main log file
            main_log_path = os.path.join(sim_dir, "simulation.log")
            main_log_file = open(main_log_path, 'w', encoding='utf-8')

            # Set environment variables for UTF-8
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'

            process = subprocess.Popen(
                cmd,
                cwd=sim_dir,
                stdout=main_log_file,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                env=env,
                start_new_session=True,
            )

            cls._stdout_files[simulation_id] = main_log_file
            cls._stderr_files[simulation_id] = None

            state.process_pid = process.pid
            state.runner_status = RunnerStatus.RUNNING
            cls._processes[simulation_id] = process
            cls._save_run_state(state)

            # Start monitor thread
            monitor_thread = threading.Thread(
                target=cls._monitor_simulation,
                args=(simulation_id,),
                daemon=True
            )
            monitor_thread.start()
            cls._monitor_threads[simulation_id] = monitor_thread

            logger.info(f"Deliberation started: {simulation_id}, pid={process.pid}")

        except Exception as e:
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)
            raise

        return state

    @classmethod
    def _monitor_simulation(cls, simulation_id: str):
        """Monitor deliberation process, parse action logs"""
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)

        # Deliberation actions log
        deliberation_actions_log = os.path.join(sim_dir, "deliberation", "actions.jsonl")

        process = cls._processes.get(simulation_id)
        state = cls.get_run_state(simulation_id)

        if not process or not state:
            return

        log_position = 0

        try:
            while process.poll() is None:  # Process still running
                if os.path.exists(deliberation_actions_log):
                    log_position = cls._read_action_log(
                        deliberation_actions_log, log_position, state
                    )

                cls._save_run_state(state)
                time.sleep(2)

            # Final read after process ends
            if os.path.exists(deliberation_actions_log):
                cls._read_action_log(deliberation_actions_log, log_position, state)

            # Process ended
            exit_code = process.returncode

            if exit_code == 0:
                state.runner_status = RunnerStatus.COMPLETED
                state.completed_at = datetime.now().isoformat()
                logger.info(f"Deliberation completed: {simulation_id}")
            else:
                state.runner_status = RunnerStatus.FAILED
                main_log_path = os.path.join(sim_dir, "simulation.log")
                error_info = ""
                try:
                    if os.path.exists(main_log_path):
                        with open(main_log_path, 'r', encoding='utf-8') as f:
                            error_info = f.read()[-2000:]
                except Exception:
                    pass
                state.error = f"Exit code: {exit_code}, Error: {error_info}"
                logger.error(f"Deliberation failed: {simulation_id}, error={state.error}")

            cls._save_run_state(state)

        except Exception as e:
            logger.error(f"Monitor thread exception: {simulation_id}, error={str(e)}")
            state.runner_status = RunnerStatus.FAILED
            state.error = str(e)
            cls._save_run_state(state)

        finally:
            # Stop graph memory updater
            if cls._graph_memory_enabled.get(simulation_id, False):
                try:
                    ZepGraphMemoryManager.stop_updater(simulation_id)
                    logger.info(f"Stopped graph memory update: simulation_id={simulation_id}")
                except Exception as e:
                    logger.error(f"Failed to stop graph memory updater: {e}")
                cls._graph_memory_enabled.pop(simulation_id, None)

            # Clean up process resources
            cls._processes.pop(simulation_id, None)
            cls._action_queues.pop(simulation_id, None)

            # Close log file handles
            if simulation_id in cls._stdout_files:
                try:
                    cls._stdout_files[simulation_id].close()
                except Exception:
                    pass
                cls._stdout_files.pop(simulation_id, None)
            if simulation_id in cls._stderr_files and cls._stderr_files[simulation_id]:
                try:
                    cls._stderr_files[simulation_id].close()
                except Exception:
                    pass
                cls._stderr_files.pop(simulation_id, None)

    @classmethod
    def _read_action_log(
        cls,
        log_path: str,
        position: int,
        state: SimulationRunState,
    ) -> int:
        """
        Read deliberation action log file.

        Args:
            log_path: Action log file path
            position: Last read position
            state: Run state object

        Returns:
            New read position
        """
        # Check if graph memory update is enabled
        graph_memory_enabled = cls._graph_memory_enabled.get(state.simulation_id, False)
        graph_updater = None
        if graph_memory_enabled:
            graph_updater = ZepGraphMemoryManager.get_updater(state.simulation_id)

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                f.seek(position)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            action_data = json.loads(line)

                            # Handle event-type entries
                            if "event_type" in action_data:
                                event_type = action_data.get("event_type")

                                # Phase start event
                                if event_type == "phase_start":
                                    state.current_phase = action_data.get("phase", 0)
                                    state.current_phase_name = action_data.get("phase_name", "")
                                    state.phase_round = 0
                                    logger.info(f"Phase started: {state.current_phase} - {state.current_phase_name}")

                                # Phase end event
                                elif event_type == "phase_end":
                                    phase_num = action_data.get("phase", 0)
                                    logger.info(f"Phase completed: {phase_num} - {action_data.get('phase_name', '')}")

                                # Round end event
                                elif event_type == "round_end":
                                    round_num = action_data.get("round", 0)
                                    state.phase_round = round_num
                                    if round_num > state.current_round:
                                        state.current_round = round_num

                                # COA proposed event
                                elif event_type == "coa_proposed":
                                    state.coas_proposed = action_data.get("coa_count", state.coas_proposed + 1)

                                # COA selected event
                                elif event_type == "coa_selected":
                                    state.selected_coa = action_data.get("selected_coa", "")

                                # Deliberation end event
                                elif event_type == "simulation_end" or event_type == "deliberation_end":
                                    state.runner_status = RunnerStatus.COMPLETED
                                    state.completed_at = datetime.now().isoformat()
                                    logger.info(f"Deliberation completed: {state.simulation_id}")

                                continue

                            # Parse agent action
                            action = AgentAction(
                                phase=action_data.get("phase", 0),
                                phase_name=action_data.get("phase_name", ""),
                                round_num=action_data.get("round", 0),
                                timestamp=action_data.get("timestamp", datetime.now().isoformat()),
                                agent_id=action_data.get("agent_id", 0),
                                agent_name=action_data.get("agent_name", ""),
                                agent_role=action_data.get("agent_role", ""),
                                action_type=action_data.get("action_type", ""),
                                content=action_data.get("content", ""),
                                references=action_data.get("references", []),
                                confidence=action_data.get("confidence", 0.0),
                                risk_assessment=action_data.get("risk_assessment", ""),
                                success=action_data.get("success", True),
                            )
                            state.add_action(action)

                            # Update round counter
                            if action.round_num and action.round_num > state.current_round:
                                state.current_round = action.round_num

                            # Update phase info
                            if action.phase > state.current_phase:
                                state.current_phase = action.phase
                                state.current_phase_name = action.phase_name

                            # Track COA proposals
                            if action.action_type == "propose_coa":
                                state.coas_proposed += 1

                            # Send to graph memory if enabled
                            if graph_updater:
                                graph_updater.add_activity_from_dict(action_data, "deliberation")

                        except json.JSONDecodeError:
                            pass
                return f.tell()
        except Exception as e:
            logger.warning(f"Failed to read action log: {log_path}, error={e}")
            return position

    @classmethod
    def _terminate_process(cls, process: subprocess.Popen, simulation_id: str, timeout: int = 10):
        """
        Cross-platform process termination.
        """
        if IS_WINDOWS:
            logger.info(f"Terminating process tree (Windows): simulation={simulation_id}, pid={process.pid}")
            try:
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T'],
                    capture_output=True,
                    timeout=5
                )
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process not responding, force killing: {simulation_id}")
                    subprocess.run(
                        ['taskkill', '/F', '/PID', str(process.pid), '/T'],
                        capture_output=True,
                        timeout=5
                    )
                    process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"taskkill failed, trying terminate: {e}")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        else:
            pgid = os.getpgid(process.pid)
            logger.info(f"Terminating process group (Unix): simulation={simulation_id}, pgid={pgid}")

            os.killpg(pgid, signal.SIGTERM)

            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process group not responding to SIGTERM, force killing: {simulation_id}")
                os.killpg(pgid, signal.SIGKILL)
                process.wait(timeout=5)

    @classmethod
    def stop_simulation(cls, simulation_id: str) -> SimulationRunState:
        """Stop deliberation"""
        state = cls.get_run_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        if state.runner_status not in [RunnerStatus.RUNNING, RunnerStatus.PAUSED]:
            raise ValueError(f"Simulation not running: {simulation_id}, status={state.runner_status}")

        state.runner_status = RunnerStatus.STOPPING
        cls._save_run_state(state)

        # Terminate process
        process = cls._processes.get(simulation_id)
        if process and process.poll() is None:
            try:
                cls._terminate_process(process, simulation_id)
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.error(f"Failed to terminate process group: {simulation_id}, error={e}")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception:
                    process.kill()

        state.runner_status = RunnerStatus.STOPPED
        state.completed_at = datetime.now().isoformat()
        cls._save_run_state(state)

        # Stop graph memory updater
        if cls._graph_memory_enabled.get(simulation_id, False):
            try:
                ZepGraphMemoryManager.stop_updater(simulation_id)
                logger.info(f"Stopped graph memory update: simulation_id={simulation_id}")
            except Exception as e:
                logger.error(f"Failed to stop graph memory updater: {e}")
            cls._graph_memory_enabled.pop(simulation_id, None)

        logger.info(f"Deliberation stopped: {simulation_id}")
        return state

    @classmethod
    def _read_actions_from_file(
        cls,
        file_path: str,
        agent_id: Optional[int] = None,
        agent_role: Optional[str] = None,
        phase: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        Read actions from a single action log file.

        Args:
            file_path: Action log file path
            agent_id: Filter by agent ID
            agent_role: Filter by agent role code
            phase: Filter by phase number
            round_num: Filter by round number
        """
        if not os.path.exists(file_path):
            return []

        actions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)

                    # Skip event records
                    if "event_type" in data:
                        continue

                    # Skip records without agent_id
                    if "agent_id" not in data:
                        continue

                    # Apply filters
                    if agent_id is not None and data.get("agent_id") != agent_id:
                        continue
                    if agent_role and data.get("agent_role") != agent_role:
                        continue
                    if phase is not None and data.get("phase") != phase:
                        continue
                    if round_num is not None and data.get("round") != round_num:
                        continue

                    actions.append(AgentAction(
                        phase=data.get("phase", 0),
                        phase_name=data.get("phase_name", ""),
                        round_num=data.get("round", 0),
                        timestamp=data.get("timestamp", ""),
                        agent_id=data.get("agent_id", 0),
                        agent_name=data.get("agent_name", ""),
                        agent_role=data.get("agent_role", ""),
                        action_type=data.get("action_type", ""),
                        content=data.get("content", ""),
                        references=data.get("references", []),
                        confidence=data.get("confidence", 0.0),
                        risk_assessment=data.get("risk_assessment", ""),
                        success=data.get("success", True),
                    ))

                except json.JSONDecodeError:
                    continue

        return actions

    @classmethod
    def get_all_actions(
        cls,
        simulation_id: str,
        platform: Optional[str] = None,  # kept for API compat, ignored
        agent_id: Optional[int] = None,
        agent_role: Optional[str] = None,
        phase: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        Get complete action history from deliberation log.

        Args:
            simulation_id: Simulation ID
            platform: Ignored (backward compatibility)
            agent_id: Filter by agent ID
            agent_role: Filter by agent role code
            phase: Filter by phase number
            round_num: Filter by round number

        Returns:
            Complete action list (sorted by timestamp, newest first)
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)

        # Read from deliberation actions log
        deliberation_log = os.path.join(sim_dir, "deliberation", "actions.jsonl")
        actions = cls._read_actions_from_file(
            deliberation_log,
            agent_id=agent_id,
            agent_role=agent_role,
            phase=phase,
            round_num=round_num
        )

        # Fallback: try legacy locations
        if not actions:
            # Try old single-file format
            legacy_log = os.path.join(sim_dir, "actions.jsonl")
            actions = cls._read_actions_from_file(
                legacy_log,
                agent_id=agent_id,
                agent_role=agent_role,
                phase=phase,
                round_num=round_num
            )

        # Sort by timestamp (newest first)
        actions.sort(key=lambda x: x.timestamp, reverse=True)

        return actions

    @classmethod
    def get_actions(
        cls,
        simulation_id: str,
        limit: int = 100,
        offset: int = 0,
        platform: Optional[str] = None,
        agent_id: Optional[int] = None,
        round_num: Optional[int] = None
    ) -> List[AgentAction]:
        """
        Get action history with pagination.
        """
        actions = cls.get_all_actions(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            round_num=round_num
        )

        return actions[offset:offset + limit]

    @classmethod
    def get_timeline(
        cls,
        simulation_id: str,
        start_round: int = 0,
        end_round: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get deliberation timeline grouped by phase.
        """
        actions = cls.get_actions(simulation_id, limit=10000)

        # Group by phase
        phases: Dict[int, Dict[str, Any]] = {}

        for action in actions:
            phase_num = action.phase

            if phase_num not in phases:
                phases[phase_num] = {
                    "phase": phase_num,
                    "phase_name": action.phase_name,
                    "actions_count": 0,
                    "active_agents": set(),
                    "action_types": {},
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }

            p = phases[phase_num]
            p["actions_count"] += 1
            p["active_agents"].add(action.agent_id)
            p["action_types"][action.action_type] = p["action_types"].get(action.action_type, 0) + 1
            p["last_action_time"] = action.timestamp

        # Convert to list
        result = []
        for phase_num in sorted(phases.keys()):
            p = phases[phase_num]
            result.append({
                "phase": phase_num,
                "phase_name": p["phase_name"],
                "actions_count": p["actions_count"],
                "active_agents_count": len(p["active_agents"]),
                "active_agents": list(p["active_agents"]),
                "action_types": p["action_types"],
                "first_action_time": p["first_action_time"],
                "last_action_time": p["last_action_time"],
            })

        return result

    @classmethod
    def get_agent_stats(cls, simulation_id: str) -> List[Dict[str, Any]]:
        """
        Get per-agent statistics.
        """
        actions = cls.get_actions(simulation_id, limit=10000)

        agent_stats: Dict[int, Dict[str, Any]] = {}

        for action in actions:
            agent_id = action.agent_id

            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": action.agent_name,
                    "agent_role": action.agent_role,
                    "total_actions": 0,
                    "action_types": {},
                    "phases_active": set(),
                    "avg_confidence": 0.0,
                    "confidence_sum": 0.0,
                    "first_action_time": action.timestamp,
                    "last_action_time": action.timestamp,
                }

            stats = agent_stats[agent_id]
            stats["total_actions"] += 1
            stats["action_types"][action.action_type] = stats["action_types"].get(action.action_type, 0) + 1
            stats["phases_active"].add(action.phase)
            stats["confidence_sum"] += action.confidence
            stats["last_action_time"] = action.timestamp

        # Calculate averages and convert sets
        result = []
        for stats in sorted(agent_stats.values(), key=lambda x: x["total_actions"], reverse=True):
            stats["avg_confidence"] = round(stats["confidence_sum"] / max(stats["total_actions"], 1), 2)
            stats["phases_active"] = sorted(list(stats["phases_active"]))
            del stats["confidence_sum"]
            result.append(stats)

        return result

    @classmethod
    def cleanup_simulation_logs(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Clean up deliberation run logs (for forcing a restart).

        Deletes: run_state.json, deliberation/, simulation.log
        Preserves: config files, agent profiles
        """
        import shutil

        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)

        if not os.path.exists(sim_dir):
            return {"success": True, "message": "Simulation directory does not exist"}

        cleaned_files = []
        errors = []

        # Files to delete
        files_to_delete = [
            "run_state.json",
            "simulation.log",
            "stdout.log",
            "stderr.log",
            "env_status.json",
        ]

        # Directories to clean
        dirs_to_clean = ["deliberation", "twitter", "reddit"]

        for filename in files_to_delete:
            file_path = os.path.join(sim_dir, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned_files.append(filename)
                except Exception as e:
                    errors.append(f"Failed to delete {filename}: {str(e)}")

        # Clean action log directories
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(sim_dir, dir_name)
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    cleaned_files.append(f"{dir_name}/")
                except Exception as e:
                    errors.append(f"Failed to delete {dir_name}/: {str(e)}")

        # Clear in-memory state
        if simulation_id in cls._run_states:
            del cls._run_states[simulation_id]

        logger.info(f"Cleaned simulation logs: {simulation_id}, deleted: {cleaned_files}")

        return {
            "success": len(errors) == 0,
            "cleaned_files": cleaned_files,
            "errors": errors if errors else None
        }

    # Prevent duplicate cleanup
    _cleanup_done = False

    @classmethod
    def cleanup_all_simulations(cls):
        """
        Clean up all running simulation processes.
        Called on server shutdown.
        """
        if cls._cleanup_done:
            return
        cls._cleanup_done = True

        has_processes = bool(cls._processes)
        has_updaters = bool(cls._graph_memory_enabled)

        if not has_processes and not has_updaters:
            return

        logger.info("Cleaning up all simulation processes...")

        # Stop all graph memory updaters
        try:
            ZepGraphMemoryManager.stop_all()
        except Exception as e:
            logger.error(f"Failed to stop graph memory updaters: {e}")
        cls._graph_memory_enabled.clear()

        # Copy dict to avoid modification during iteration
        processes = list(cls._processes.items())

        for simulation_id, process in processes:
            try:
                if process.poll() is None:
                    logger.info(f"Terminating simulation process: {simulation_id}, pid={process.pid}")

                    try:
                        cls._terminate_process(process, simulation_id, timeout=5)
                    except (ProcessLookupError, OSError):
                        try:
                            process.terminate()
                            process.wait(timeout=3)
                        except Exception:
                            process.kill()

                    # Update run_state.json
                    state = cls.get_run_state(simulation_id)
                    if state:
                        state.runner_status = RunnerStatus.STOPPED
                        state.completed_at = datetime.now().isoformat()
                        state.error = "Server shutdown, deliberation terminated"
                        cls._save_run_state(state)

                    # Also update state.json
                    try:
                        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
                        state_file = os.path.join(sim_dir, "state.json")
                        if os.path.exists(state_file):
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state_data = json.load(f)
                            state_data['status'] = 'stopped'
                            state_data['updated_at'] = datetime.now().isoformat()
                            with open(state_file, 'w', encoding='utf-8') as f:
                                json.dump(state_data, f, indent=2, ensure_ascii=False)
                    except Exception as state_err:
                        logger.warning(f"Failed to update state.json: {simulation_id}, error={state_err}")

            except Exception as e:
                logger.error(f"Failed to clean up process: {simulation_id}, error={e}")

        # Clean up file handles
        for simulation_id, file_handle in list(cls._stdout_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stdout_files.clear()

        for simulation_id, file_handle in list(cls._stderr_files.items()):
            try:
                if file_handle:
                    file_handle.close()
            except Exception:
                pass
        cls._stderr_files.clear()

        cls._processes.clear()
        cls._action_queues.clear()

        logger.info("Simulation process cleanup complete")

    @classmethod
    def register_cleanup(cls):
        """
        Register cleanup function.
        Called on Flask app startup to ensure all simulation processes are terminated on shutdown.
        """
        global _cleanup_registered

        if _cleanup_registered:
            return

        is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        is_debug_mode = os.environ.get('FLASK_DEBUG') == '1' or os.environ.get('WERKZEUG_RUN_MAIN') is not None

        if is_debug_mode and not is_reloader_process:
            _cleanup_registered = True
            return

        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sighup = None
        has_sighup = hasattr(signal, 'SIGHUP')
        if has_sighup:
            original_sighup = signal.getsignal(signal.SIGHUP)

        def cleanup_handler(signum=None, frame=None):
            if cls._processes or cls._graph_memory_enabled:
                logger.info(f"Received signal {signum}, starting cleanup...")
            cls.cleanup_all_simulations()

            if signum == signal.SIGINT and callable(original_sigint):
                original_sigint(signum, frame)
            elif signum == signal.SIGTERM and callable(original_sigterm):
                original_sigterm(signum, frame)
            elif has_sighup and signum == signal.SIGHUP:
                if callable(original_sighup):
                    original_sighup(signum, frame)
                else:
                    sys.exit(0)
            else:
                raise KeyboardInterrupt

        atexit.register(cls.cleanup_all_simulations)

        try:
            signal.signal(signal.SIGTERM, cleanup_handler)
            signal.signal(signal.SIGINT, cleanup_handler)
            if has_sighup:
                signal.signal(signal.SIGHUP, cleanup_handler)
        except ValueError:
            logger.warning("Cannot register signal handlers (not in main thread), using atexit only")

        _cleanup_registered = True

    @classmethod
    def get_running_simulations(cls) -> List[str]:
        """Get list of all running simulation IDs"""
        running = []
        for sim_id, process in cls._processes.items():
            if process.poll() is None:
                running.append(sim_id)
        return running

    # ============== Interview Functions ==============

    @classmethod
    def check_env_alive(cls, simulation_id: str) -> bool:
        """
        Check if deliberation environment is alive (can receive Interview commands).
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return False

        ipc_client = SimulationIPCClient(sim_dir)
        return ipc_client.check_env_alive()

    @classmethod
    def get_env_status_detail(cls, simulation_id: str) -> Dict[str, Any]:
        """
        Get detailed status of the deliberation environment.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        status_file = os.path.join(sim_dir, "env_status.json")

        default_status = {
            "status": "stopped",
            "deliberation_available": False,
            "timestamp": None
        }

        if not os.path.exists(status_file):
            return default_status

        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            return {
                "status": status.get("status", "stopped"),
                "deliberation_available": status.get("deliberation_available",
                    status.get("twitter_available", False)),  # backward compat
                "timestamp": status.get("timestamp")
            }
        except (json.JSONDecodeError, OSError):
            return default_status

    @classmethod
    def interview_agent(
        cls,
        simulation_id: str,
        agent_id: int,
        prompt: str,
        platform: str = None,  # kept for API compat
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """
        Interview a single agent (post-deliberation Q&A).

        Args:
            simulation_id: Simulation ID
            agent_id: Agent ID
            prompt: Interview question
            platform: Ignored (backward compatibility)
            timeout: Timeout in seconds
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation not found: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Deliberation environment not running: {simulation_id}")

        logger.info(f"Sending interview command: simulation_id={simulation_id}, agent_id={agent_id}")

        response = ipc_client.send_interview(
            agent_id=agent_id,
            prompt=prompt,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "agent_id": agent_id,
                "prompt": prompt,
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "agent_id": agent_id,
                "prompt": prompt,
                "error": response.error,
                "timestamp": response.timestamp
            }

    @classmethod
    def interview_agents_batch(
        cls,
        simulation_id: str,
        interviews: List[Dict[str, Any]],
        platform: str = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Batch interview multiple agents.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation not found: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            raise ValueError(f"Deliberation environment not running: {simulation_id}")

        logger.info(f"Sending batch interview: simulation_id={simulation_id}, count={len(interviews)}")

        response = ipc_client.send_batch_interview(
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )

        if response.status.value == "completed":
            return {
                "success": True,
                "interviews_count": len(interviews),
                "result": response.result,
                "timestamp": response.timestamp
            }
        else:
            return {
                "success": False,
                "interviews_count": len(interviews),
                "error": response.error,
                "timestamp": response.timestamp
            }

    @classmethod
    def interview_all_agents(
        cls,
        simulation_id: str,
        prompt: str,
        platform: str = None,
        timeout: float = 180.0
    ) -> Dict[str, Any]:
        """
        Interview all agents with the same question.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation not found: {simulation_id}")

        # Try agents.json first, fall back to config
        agents_path = os.path.join(sim_dir, "agents.json")
        config_path = os.path.join(sim_dir, "deliberation_config.json")
        if not os.path.exists(config_path):
            config_path = os.path.join(sim_dir, "simulation_config.json")

        interviews = []

        if os.path.exists(agents_path):
            with open(agents_path, 'r', encoding='utf-8') as f:
                agents = json.load(f)
            for agent in agents:
                agent_id = agent.get("agent_id")
                if agent_id is not None:
                    interviews.append({
                        "agent_id": agent_id,
                        "prompt": prompt
                    })
        elif os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            agent_configs = config.get("agent_configs", [])
            for agent_config in agent_configs:
                agent_id = agent_config.get("agent_id")
                if agent_id is not None:
                    interviews.append({
                        "agent_id": agent_id,
                        "prompt": prompt
                    })

        if not interviews:
            raise ValueError(f"No agents found for: {simulation_id}")

        logger.info(f"Sending global interview: simulation_id={simulation_id}, agent_count={len(interviews)}")

        return cls.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=interviews,
            platform=platform,
            timeout=timeout
        )

    @classmethod
    def close_simulation_env(
        cls,
        simulation_id: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Close the deliberation environment gracefully.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise ValueError(f"Simulation not found: {simulation_id}")

        ipc_client = SimulationIPCClient(sim_dir)

        if not ipc_client.check_env_alive():
            return {
                "success": True,
                "message": "Environment already closed"
            }

        logger.info(f"Sending close environment command: simulation_id={simulation_id}")

        try:
            response = ipc_client.send_close_env(timeout=timeout)

            return {
                "success": response.status.value == "completed",
                "message": "Close environment command sent",
                "result": response.result,
                "timestamp": response.timestamp
            }
        except TimeoutError:
            return {
                "success": True,
                "message": "Close command sent (response timed out, environment may be shutting down)"
            }

    @classmethod
    def get_interview_history(
        cls,
        simulation_id: str,
        platform: str = None,
        agent_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get interview history from deliberation log.

        For tactical deliberation, interviews are stored in the deliberation actions log
        rather than in a separate database.
        """
        sim_dir = os.path.join(cls.RUN_STATE_DIR, simulation_id)
        results = []

        # Try reading from deliberation interview log
        interview_log = os.path.join(sim_dir, "deliberation", "interviews.jsonl")
        if os.path.exists(interview_log):
            try:
                with open(interview_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if agent_id is not None and data.get("agent_id") != agent_id:
                                continue
                            results.append({
                                "agent_id": data.get("agent_id"),
                                "agent_role": data.get("agent_role", ""),
                                "response": data.get("response", ""),
                                "prompt": data.get("prompt", ""),
                                "timestamp": data.get("timestamp", ""),
                            })
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"Failed to read interview history: {e}")

        # Fallback: try legacy SQLite databases
        if not results:
            import sqlite3
            for p in ["twitter", "reddit"]:
                if platform and platform != p:
                    continue
                db_path = os.path.join(sim_dir, f"{p}_simulation.db")
                if not os.path.exists(db_path):
                    continue
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    if agent_id is not None:
                        cursor.execute(
                            "SELECT user_id, info, created_at FROM trace WHERE action = 'interview' AND user_id = ? ORDER BY created_at DESC LIMIT ?",
                            (agent_id, limit)
                        )
                    else:
                        cursor.execute(
                            "SELECT user_id, info, created_at FROM trace WHERE action = 'interview' ORDER BY created_at DESC LIMIT ?",
                            (limit,)
                        )
                    for user_id, info_json, created_at in cursor.fetchall():
                        try:
                            info = json.loads(info_json) if info_json else {}
                        except json.JSONDecodeError:
                            info = {"raw": info_json}
                        results.append({
                            "agent_id": user_id,
                            "response": info.get("response", info),
                            "prompt": info.get("prompt", ""),
                            "timestamp": created_at,
                        })
                    conn.close()
                except Exception as e:
                    logger.error(f"Failed to read interview history from {p} DB: {e}")

        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        if len(results) > limit:
            results = results[:limit]

        return results
