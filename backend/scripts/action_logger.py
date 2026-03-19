"""
Tactical Deliberation Action Logger
Records each staff officer's actions during MDMP deliberation for backend monitoring.

Log structure:
    sim_xxx/
    ├── deliberation/
    │   ├── actions.jsonl    # Deliberation action log
    │   ├── results.json     # Final deliberation results
    │   └── coa_matrix.json  # COA comparison matrix
    ├── simulation.log       # Main process log
    └── run_state.json       # Run state (for API queries)
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List


class DeliberationActionLogger:
    """Tactical deliberation action logger"""

    def __init__(self, base_dir: str):
        """
        Initialize logger.

        Args:
            base_dir: Simulation directory base path
        """
        self.base_dir = base_dir
        self.log_dir = os.path.join(base_dir, "deliberation")
        self.log_path = os.path.join(self.log_dir, "actions.jsonl")
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(self.log_dir, exist_ok=True)

    def log_action(
        self,
        phase: int,
        phase_name: str,
        round_num: int,
        agent_id: int,
        agent_name: str,
        agent_role: str,
        action_type: str,
        content: str = "",
        references: Optional[List[str]] = None,
        confidence: float = 0.0,
        risk_assessment: str = "",
        success: bool = True,
    ):
        """Record a deliberation action"""
        entry = {
            "phase": phase,
            "phase_name": phase_name,
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_role": agent_role,
            "action_type": action_type,
            "content": content,
            "references": references or [],
            "confidence": confidence,
            "risk_assessment": risk_assessment,
            "success": success,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_phase_start(self, phase: int, phase_name: str, active_roles: Optional[List[str]] = None):
        """Record phase start"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "phase_start",
            "phase": phase,
            "phase_name": phase_name,
            "active_roles": active_roles or [],
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_phase_end(self, phase: int, phase_name: str, rounds_completed: int, actions_count: int):
        """Record phase end"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "phase_end",
            "phase": phase,
            "phase_name": phase_name,
            "rounds_completed": rounds_completed,
            "actions_count": actions_count,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_round_start(self, phase: int, round_num: int):
        """Record round start within a phase"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "round_start",
            "phase": phase,
            "round": round_num,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_round_end(self, phase: int, round_num: int, actions_count: int):
        """Record round end within a phase"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "round_end",
            "phase": phase,
            "round": round_num,
            "actions_count": actions_count,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_coa_proposed(self, coa_id: str, coa_name: str, proposer_role: str, coa_count: int):
        """Record a new COA proposal"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "coa_proposed",
            "coa_id": coa_id,
            "coa_name": coa_name,
            "proposer_role": proposer_role,
            "coa_count": coa_count,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_coa_selected(self, selected_coa: str, rationale: str = ""):
        """Record COA selection by commander"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "coa_selected",
            "selected_coa": selected_coa,
            "rationale": rationale,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_deliberation_start(self, config: Dict[str, Any]):
        """Record deliberation start"""
        phases = config.get("phases", [])
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "simulation_start",
            "total_phases": len(phases),
            "total_rounds": sum(p.get("max_rounds", 3) for p in phases),
            "mission_type": config.get("mission_config", {}).get("mission_type", ""),
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def log_deliberation_end(self, total_phases: int, total_actions: int, selected_coa: str = ""):
        """Record deliberation end"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "deliberation_end",
            "total_phases": total_phases,
            "total_actions": total_actions,
            "selected_coa": selected_coa,
        }

        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')


class SimulationLogManager:
    """
    Simulation log manager.
    Manages all log files for a deliberation session.
    """

    def __init__(self, simulation_dir: str):
        self.simulation_dir = simulation_dir
        self.deliberation_logger: Optional[DeliberationActionLogger] = None
        self._main_logger: Optional[logging.Logger] = None

        self._setup_main_logger()

    def _setup_main_logger(self):
        """Set up main simulation logger"""
        log_path = os.path.join(self.simulation_dir, "simulation.log")

        self._main_logger = logging.getLogger(f"simulation.{os.path.basename(self.simulation_dir)}")
        self._main_logger.setLevel(logging.INFO)
        self._main_logger.handlers.clear()

        file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self._main_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        self._main_logger.addHandler(console_handler)

        self._main_logger.propagate = False

    def get_deliberation_logger(self) -> DeliberationActionLogger:
        """Get deliberation action logger"""
        if self.deliberation_logger is None:
            self.deliberation_logger = DeliberationActionLogger(self.simulation_dir)
        return self.deliberation_logger

    # Legacy compatibility
    def get_twitter_logger(self):
        """Legacy compat — returns deliberation logger"""
        return self.get_deliberation_logger()

    def get_reddit_logger(self):
        """Legacy compat — returns deliberation logger"""
        return self.get_deliberation_logger()

    def log(self, message: str, level: str = "info"):
        if self._main_logger:
            getattr(self._main_logger, level.lower(), self._main_logger.info)(message)

    def info(self, message: str):
        self.log(message, "info")

    def warning(self, message: str):
        self.log(message, "warning")

    def error(self, message: str):
        self.log(message, "error")

    def debug(self, message: str):
        self.log(message, "debug")


# ============ Legacy interface compat ============

class PlatformActionLogger:
    """Legacy compatibility wrapper — redirects to DeliberationActionLogger."""

    def __init__(self, platform: str, base_dir: str):
        self.platform = platform
        self._delegate = DeliberationActionLogger(base_dir)

    def log_action(self, round_num: int, agent_id: int, agent_name: str,
                   action_type: str, action_args: Optional[Dict[str, Any]] = None,
                   result: Optional[str] = None, success: bool = True):
        self._delegate.log_action(
            phase=0, phase_name=self.platform, round_num=round_num,
            agent_id=agent_id, agent_name=agent_name, agent_role="",
            action_type=action_type, content=str(action_args) if action_args else "",
            success=success,
        )

    def log_round_start(self, round_num: int, simulated_hour: int):
        self._delegate.log_round_start(phase=0, round_num=round_num)

    def log_round_end(self, round_num: int, actions_count: int):
        self._delegate.log_round_end(phase=0, round_num=round_num, actions_count=actions_count)

    def log_simulation_start(self, config: Dict[str, Any]):
        self._delegate.log_deliberation_start(config)

    def log_simulation_end(self, total_rounds: int, total_actions: int):
        self._delegate.log_deliberation_end(total_phases=0, total_actions=total_actions)


class ActionLogger:
    """Legacy action logger — redirects to DeliberationActionLogger."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        base_dir = os.path.dirname(log_path) or "."
        self._delegate = DeliberationActionLogger(base_dir)

    def log_action(self, round_num: int, platform: str, agent_id: int,
                   agent_name: str, action_type: str,
                   action_args: Optional[Dict[str, Any]] = None,
                   result: Optional[str] = None, success: bool = True):
        self._delegate.log_action(
            phase=0, phase_name=platform, round_num=round_num,
            agent_id=agent_id, agent_name=agent_name, agent_role="",
            action_type=action_type, content=str(action_args) if action_args else "",
            success=success,
        )


_global_logger: Optional[ActionLogger] = None


def get_logger(log_path: Optional[str] = None) -> ActionLogger:
    """Get global logger instance (legacy compat)"""
    global _global_logger

    if log_path:
        _global_logger = ActionLogger(log_path)

    if _global_logger is None:
        _global_logger = ActionLogger("actions.jsonl")

    return _global_logger
