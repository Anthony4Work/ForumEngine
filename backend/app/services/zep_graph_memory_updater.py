"""
Graph Memory Update Service
Updates knowledge graph with deliberation activities from tactical agents.
"""

import os
import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Queue, Empty

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from ..config import Config
from ..utils.graphiti_client import get_graphiti, run_async
from ..utils.logger import get_logger

logger = get_logger('mirofish.graph_memory_updater')


@dataclass
class AgentActivity:
    """Agent activity record for tactical deliberation"""
    platform: str           # deliberation (kept for backward compat)
    agent_id: int
    agent_name: str
    action_type: str        # propose_coa, assess_threat, etc.
    action_args: Dict[str, Any]
    round_num: int
    timestamp: str

    def to_episode_text(self) -> str:
        """
        Convert activity to natural language text for graph ingestion.
        Graphiti will extract entities and relationships from this text.
        """
        agent_role = self.action_args.get("agent_role", "")
        content = self.action_args.get("content", "")
        confidence = self.action_args.get("confidence", 0)
        risk = self.action_args.get("risk_assessment", "")
        references = self.action_args.get("references", [])
        phase_name = self.action_args.get("phase_name", "")

        # Build role prefix
        role_prefix = f"{self.agent_name}"
        if agent_role:
            role_prefix = f"{agent_role} {self.agent_name}"

        # Action-specific descriptions
        desc = self._describe_action(content, confidence, risk, references, phase_name)

        return f"{role_prefix}: {desc}"

    def _describe_action(self, content: str, confidence: float, risk: str,
                          references: list, phase_name: str) -> str:
        """Generate tactical description based on action type."""
        action_type = self.action_type.lower()

        # COA actions
        if action_type == "propose_coa":
            return f"Proposed a course of action during {phase_name}: {content}"
        elif action_type == "refine_coa":
            return f"Refined a course of action: {content}"
        elif action_type == "score_coa":
            return f"Scored a course of action (confidence: {confidence}): {content}"
        elif action_type == "decide_coa":
            return f"Selected a course of action: {content}"

        # Analysis actions
        elif action_type == "analyze_terrain":
            return f"Conducted terrain analysis: {content}"
        elif action_type == "assess_threat":
            return f"Assessed threat (risk: {risk}): {content}"
        elif action_type == "assess_logistics":
            return f"Assessed logistics feasibility: {content}"
        elif action_type == "assess_comms":
            return f"Assessed communications and C2 networks: {content}"
        elif action_type == "identify_key_terrain":
            return f"Identified key terrain: {content}"

        # Wargaming
        elif action_type == "wargame_move":
            return f"Wargamed a friendly move: {content}"
        elif action_type == "wargame_counter":
            return f"Wargamed an enemy counter-move: {content}"

        # Evaluation
        elif action_type == "evaluate_risk":
            return f"Evaluated risk (assessment: {risk}): {content}"
        elif action_type == "challenge_assumption":
            return f"Challenged an assumption: {content}"

        # Intelligence
        elif action_type == "request_intel":
            return f"Requested intelligence: {content}"
        elif action_type == "provide_intel":
            return f"Provided intelligence: {content}"
        elif action_type == "identify_gap":
            return f"Identified an intelligence gap: {content}"

        # Coordination
        elif action_type == "concur":
            return f"Concurred with a proposal: {content}"
        elif action_type == "dissent":
            return f"Dissented from a proposal: {content}"
        elif action_type == "recommend":
            return f"Made a recommendation: {content}"
        elif action_type == "task_organize":
            return f"Proposed task organization: {content}"

        # Generic fallback
        else:
            return f"Performed {action_type}: {content}" if content else f"Performed {action_type}"


class GraphMemoryUpdater:
    """
    Graph Memory Updater

    Monitors deliberation action logs and updates the knowledge graph with
    agent activities.  Batches activities for efficient API usage.
    """

    # Batch size (activities accumulated before sending)
    BATCH_SIZE = 5

    # Platform display names
    PLATFORM_DISPLAY_NAMES = {
        'deliberation': 'Deliberation',
        'twitter': 'World 1',
        'reddit': 'World 2',
    }

    # Send interval (seconds) to avoid excessive request rates
    SEND_INTERVAL = 0.5

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(
        self,
        graph_id: str,
        entity_types: Optional[Dict] = None,
        edge_types: Optional[Dict] = None,
        edge_type_map: Optional[Dict] = None,
    ):
        """
        Initialize updater

        Args:
            graph_id: Graph ID (used as group_id in Graphiti episodes)
            entity_types: Optional ontology entity types for add_episode
            edge_types: Optional ontology edge types for add_episode
            edge_type_map: Optional ontology edge type map for add_episode
        """
        self.graph_id = graph_id
        self.graphiti = get_graphiti()

        # Ontology parameters for add_episode
        self._entity_types = entity_types or {}
        self._edge_types = edge_types or {}
        self._edge_type_map = edge_type_map or {}

        # Activity queue
        self._activity_queue: Queue = Queue()

        # Per-source activity buffers (accumulate to BATCH_SIZE before sending)
        self._platform_buffers: Dict[str, List[AgentActivity]] = {
            'deliberation': [],
        }
        self._buffer_lock = threading.Lock()

        # Control flags
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        # Statistics
        self._total_activities = 0  # Total activities added to queue
        self._total_sent = 0        # Successfully sent batch count
        self._total_items_sent = 0  # Successfully sent activity count
        self._failed_count = 0      # Failed batch count
        self._skipped_count = 0     # Filtered/skipped activity count (DO_NOTHING)
        self._batch_count = 0       # Cumulative batch counter (used for episode name)

        logger.info(f"GraphMemoryUpdater initialized: graph_id={graph_id}, batch_size={self.BATCH_SIZE}")

    def _get_platform_display_name(self, platform: str) -> str:
        """Get display name for platform"""
        return self.PLATFORM_DISPLAY_NAMES.get(platform.lower(), platform)

    def start(self):
        """Start background worker thread"""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name=f"GraphMemoryUpdater-{self.graph_id[:8]}"
        )
        self._worker_thread.start()
        logger.info(f"GraphMemoryUpdater started: graph_id={self.graph_id}")

    def stop(self):
        """Stop background worker thread"""
        self._running = False

        # Send remaining activities
        self._flush_remaining()

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)

        logger.info(f"GraphMemoryUpdater stopped: graph_id={self.graph_id}, "
                   f"total_activities={self._total_activities}, "
                   f"batches_sent={self._total_sent}, "
                   f"items_sent={self._total_items_sent}, "
                   f"failed={self._failed_count}, "
                   f"skipped={self._skipped_count}")

    def add_activity(self, activity: AgentActivity):
        """
        Add an agent activity to the queue

        All meaningful actions are added to the queue, including:
        - CREATE_POST
        - CREATE_COMMENT
        - QUOTE_POST
        - SEARCH_POSTS
        - SEARCH_USER
        - LIKE_POST/DISLIKE_POST
        - REPOST
        - FOLLOW
        - MUTE
        - LIKE_COMMENT/DISLIKE_COMMENT

        action_args contains full context information (e.g., post content, username, etc.).

        Args:
            activity: Agent activity record
        """
        # Skip DO_NOTHING type activities
        if activity.action_type == "DO_NOTHING":
            self._skipped_count += 1
            return

        self._activity_queue.put(activity)
        self._total_activities += 1
        logger.debug(f"Added activity to graph queue: {activity.agent_name} - {activity.action_type}")

    def add_activity_from_dict(self, data: Dict[str, Any], platform: str = "deliberation"):
        """
        Add activity from parsed dict data.

        Args:
            data: Dict from actions.jsonl
            platform: Source name (deliberation/twitter/reddit)
        """
        # Skip event-type entries
        if "event_type" in data:
            return

        # Build action_args with tactical context
        action_args = data.get("action_args", {})
        # For tactical deliberation, include key fields in action_args for episode text
        if "content" in data and "content" not in action_args:
            action_args["content"] = data.get("content", "")
        if "agent_role" in data and "agent_role" not in action_args:
            action_args["agent_role"] = data.get("agent_role", "")
        if "confidence" in data and "confidence" not in action_args:
            action_args["confidence"] = data.get("confidence", 0)
        if "risk_assessment" in data and "risk_assessment" not in action_args:
            action_args["risk_assessment"] = data.get("risk_assessment", "")
        if "references" in data and "references" not in action_args:
            action_args["references"] = data.get("references", [])
        if "phase_name" in data and "phase_name" not in action_args:
            action_args["phase_name"] = data.get("phase_name", "")

        activity = AgentActivity(
            platform=platform,
            agent_id=data.get("agent_id", 0),
            agent_name=data.get("agent_name", ""),
            action_type=data.get("action_type", ""),
            action_args=action_args,
            round_num=data.get("round", 0),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )

        self.add_activity(activity)

    def _worker_loop(self):
        """Background worker loop - batch sends activities to graph by platform"""
        while self._running or not self._activity_queue.empty():
            try:
                # Try to get activity from queue (1-second timeout)
                try:
                    activity = self._activity_queue.get(timeout=1)

                    # Add activity to the corresponding platform buffer
                    platform = activity.platform.lower()
                    with self._buffer_lock:
                        if platform not in self._platform_buffers:
                            self._platform_buffers[platform] = []
                        self._platform_buffers[platform].append(activity)

                        # Check if this platform has reached batch size
                        if len(self._platform_buffers[platform]) >= self.BATCH_SIZE:
                            batch = self._platform_buffers[platform][:self.BATCH_SIZE]
                            self._platform_buffers[platform] = self._platform_buffers[platform][self.BATCH_SIZE:]
                            # Release lock before sending
                            self._send_batch_activities(batch, platform)
                            # Send interval to avoid excessive request rates
                            time.sleep(self.SEND_INTERVAL)

                except Empty:
                    pass

            except Exception as e:
                logger.error(f"Worker loop exception: {e}")
                time.sleep(1)

    def _send_batch_activities(self, activities: List[AgentActivity], platform: str):
        """
        Batch send activities to the graph (merged into a single text)

        Args:
            activities: List of agent activities
            platform: Platform name
        """
        if not activities:
            return

        # Merge multiple activities into a single text, separated by newlines
        episode_texts = [activity.to_episode_text() for activity in activities]
        combined_text = "\n".join(episode_texts)

        self._batch_count += 1

        # Send with retry
        for attempt in range(self.MAX_RETRIES):
            try:
                run_async(self.graphiti.add_episode(
                    name=f"deliberation_batch_{self._batch_count}",
                    episode_body=combined_text,
                    source=EpisodeType.text,
                    source_description="Tactical deliberation activities",
                    reference_time=datetime.now(timezone.utc),
                    group_id=self.graph_id,
                    entity_types=self._entity_types if self._entity_types else None,
                    edge_types=self._edge_types if self._edge_types else None,
                    edge_type_map=self._edge_type_map if self._edge_type_map else None,
                ))

                self._total_sent += 1
                self._total_items_sent += len(activities)
                display_name = self._get_platform_display_name(platform)
                logger.info(f"Successfully batch-sent {len(activities)} {display_name} activities to graph {self.graph_id}")
                logger.debug(f"Batch content preview: {combined_text[:200]}...")
                return

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Batch send to graph failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"Batch send to graph failed after {self.MAX_RETRIES} retries: {e}")
                    self._failed_count += 1

    def _flush_remaining(self):
        """Send remaining activities in the queue and buffers"""
        # First process remaining activities in the queue, adding them to buffers
        while not self._activity_queue.empty():
            try:
                activity = self._activity_queue.get_nowait()
                platform = activity.platform.lower()
                with self._buffer_lock:
                    if platform not in self._platform_buffers:
                        self._platform_buffers[platform] = []
                    self._platform_buffers[platform].append(activity)
            except Empty:
                break

        # Then send remaining activities in each platform buffer (even if below BATCH_SIZE)
        with self._buffer_lock:
            for platform, buffer in self._platform_buffers.items():
                if buffer:
                    display_name = self._get_platform_display_name(platform)
                    logger.info(f"Sending remaining {len(buffer)} activities for {display_name} platform")
                    self._send_batch_activities(buffer, platform)
            # Clear all buffers
            for platform in self._platform_buffers:
                self._platform_buffers[platform] = []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        with self._buffer_lock:
            buffer_sizes = {p: len(b) for p, b in self._platform_buffers.items()}

        return {
            "graph_id": self.graph_id,
            "batch_size": self.BATCH_SIZE,
            "total_activities": self._total_activities,  # Total activities added to queue
            "batches_sent": self._total_sent,            # Successfully sent batch count
            "items_sent": self._total_items_sent,        # Successfully sent activity count
            "failed_count": self._failed_count,          # Failed batch count
            "skipped_count": self._skipped_count,        # Filtered/skipped activity count (DO_NOTHING)
            "queue_size": self._activity_queue.qsize(),
            "buffer_sizes": buffer_sizes,                # Per-platform buffer sizes
            "running": self._running,
        }


class GraphMemoryManager:
    """
    Manages graph memory updaters for multiple simulations

    Each simulation can have its own updater instance
    """

    _updaters: Dict[str, GraphMemoryUpdater] = {}
    _lock = threading.Lock()

    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> GraphMemoryUpdater:
        """
        Create a graph memory updater for a simulation

        Args:
            simulation_id: Simulation ID
            graph_id: Graph ID

        Returns:
            GraphMemoryUpdater instance
        """
        with cls._lock:
            # If one already exists, stop the old one first
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()

            updater = GraphMemoryUpdater(graph_id)
            updater.start()
            cls._updaters[simulation_id] = updater

            logger.info(f"Created graph memory updater: simulation_id={simulation_id}, graph_id={graph_id}")
            return updater

    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[GraphMemoryUpdater]:
        """Get the updater for a simulation"""
        return cls._updaters.get(simulation_id)

    @classmethod
    def stop_updater(cls, simulation_id: str):
        """Stop and remove the updater for a simulation"""
        with cls._lock:
            if simulation_id in cls._updaters:
                cls._updaters[simulation_id].stop()
                del cls._updaters[simulation_id]
                logger.info(f"Stopped graph memory updater: simulation_id={simulation_id}")

    # Flag to prevent duplicate stop_all calls
    _stop_all_done = False

    @classmethod
    def stop_all(cls):
        """Stop all updaters"""
        # Prevent duplicate calls
        if cls._stop_all_done:
            return
        cls._stop_all_done = True

        with cls._lock:
            if cls._updaters:
                for simulation_id, updater in list(cls._updaters.items()):
                    try:
                        updater.stop()
                    except Exception as e:
                        logger.error(f"Failed to stop updater: simulation_id={simulation_id}, error={e}")
                cls._updaters.clear()
            logger.info("Stopped all graph memory updaters")

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all updaters"""
        return {
            sim_id: updater.get_stats()
            for sim_id, updater in cls._updaters.items()
        }


# Backward-compatible aliases
ZepGraphMemoryUpdater = GraphMemoryUpdater
ZepGraphMemoryManager = GraphMemoryManager
