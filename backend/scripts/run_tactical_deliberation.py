"""
Tactical Deliberation Engine
Replaces OASIS social media simulation with a structured MDMP
(Military Decision-Making Process) deliberation among staff officers.

This script is launched as a subprocess by simulation_runner.py.
It reads agents.json + deliberation_config.json, runs the 7-phase
MDMP deliberation, and writes results to deliberation/actions.jsonl.
"""

import os
import sys
import json
import asyncio
import time
import signal
import random
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import AsyncOpenAI

# Add parent paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.config import Config
from app.utils.logger import get_logger
from app.utils.graphiti_client import get_graphiti, run_async

logger = get_logger('mirofish.deliberation')


# ============================================================================
# T3.1 — TacticalActionType
# ============================================================================

class TacticalActionType(str, Enum):
    # Analysis (Phases 1-2)
    ANALYZE_TERRAIN = "analyze_terrain"
    ASSESS_THREAT = "assess_threat"
    ASSESS_LOGISTICS = "assess_logistics"
    ASSESS_COMMS = "assess_comms"
    IDENTIFY_KEY_TERRAIN = "identify_key_terrain"

    # COA Development (Phase 3)
    PROPOSE_COA = "propose_coa"
    REFINE_COA = "refine_coa"

    # Evaluation (Phases 4-5)
    EVALUATE_RISK = "evaluate_risk"
    CHALLENGE_ASSUMPTION = "challenge_assumption"
    WARGAME_MOVE = "wargame_move"
    WARGAME_COUNTER = "wargame_counter"
    SCORE_COA = "score_coa"

    # Decision (Phase 6)
    DECIDE_COA = "decide_coa"

    # Information
    REQUEST_INTEL = "request_intel"
    PROVIDE_INTEL = "provide_intel"
    IDENTIFY_GAP = "identify_gap"

    # Coordination
    CONCUR = "concur"
    DISSENT = "dissent"
    RECOMMEND = "recommend"
    TASK_ORGANIZE = "task_organize"

    # SME interactions
    CONSULT_SME = "consult_sme"
    SME_TESTIMONY = "sme_testimony"


# ============================================================================
# T3.2 — MDMP Phase Configuration
# ============================================================================

MDMP_PHASES = [
    {
        "phase_id": 1,
        "phase_name": "Mission Analysis",
        "description": "Restate the mission, identify specified/implied tasks, constraints, and available capabilities.",
        "max_rounds": 3,
        "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"],
        "primary_role": "XO",
        "valid_actions": [
            "analyze_terrain", "assess_threat", "assess_logistics", "assess_comms",
            "identify_key_terrain", "request_intel", "identify_gap", "concur", "dissent",
            "consult_sme",
        ],
        "completion_criteria": "Mission restated, specified/implied tasks identified, constraints listed, initial commander's guidance issued.",
    },
    {
        "phase_id": 2,
        "phase_name": "Intelligence Preparation of the Battlefield (IPB)",
        "description": "Detailed threat assessment, terrain/weather analysis, and development of enemy COAs.",
        "max_rounds": 3,
        "active_roles": ["S2", "CDR", "S3", "RED", "ENGR"],
        "primary_role": "S2",
        "valid_actions": [
            "assess_threat", "analyze_terrain", "identify_key_terrain",
            "request_intel", "provide_intel", "identify_gap", "wargame_counter",
            "consult_sme",
        ],
        "completion_criteria": "Threat assessment complete, at least one enemy COA developed, terrain analysis done.",
    },
    {
        "phase_id": 3,
        "phase_name": "COA Development",
        "description": "Generate 2-4 distinct and viable friendly courses of action.",
        "max_rounds": 5,
        "active_roles": ["S3", "CDR", "XO", "S2", "S4", "FSO", "ENGR", "CIMIC"],
        "primary_role": "S3",
        "valid_actions": [
            "propose_coa", "refine_coa", "assess_logistics", "evaluate_risk",
            "request_intel", "dissent", "recommend", "task_organize",
            "consult_sme",
        ],
        "completion_criteria": "2-4 distinct COAs developed, each with scheme of maneuver and force allocation.",
    },
    {
        "phase_id": 4,
        "phase_name": "COA Analysis (Wargaming)",
        "description": "Wargame each friendly COA against identified enemy COAs. Identify decision points and vulnerabilities.",
        "max_rounds": 5,
        "active_roles": ["RED", "S3", "S2", "FSO", "S4", "ENGR", "S6"],
        "primary_role": "RED",
        "valid_actions": [
            "wargame_move", "wargame_counter", "evaluate_risk",
            "challenge_assumption", "request_intel", "identify_gap",
            "consult_sme",
        ],
        "completion_criteria": "Each COA wargamed against at least one enemy COA, decision points identified, risks catalogued.",
    },
    {
        "phase_id": 5,
        "phase_name": "COA Comparison",
        "description": "Score each COA against weighted evaluation criteria. Build comparison matrix.",
        "max_rounds": 3,
        "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"],
        "primary_role": "XO",
        "valid_actions": [
            "score_coa", "evaluate_risk", "concur", "dissent", "recommend",
            "consult_sme",
        ],
        "completion_criteria": "All COAs scored against all criteria, comparison matrix complete, ranking established.",
    },
    {
        "phase_id": 6,
        "phase_name": "COA Decision",
        "description": "Commander selects a COA and issues planning guidance.",
        "max_rounds": 2,
        "active_roles": ["CDR", "XO"],
        "primary_role": "CDR",
        "valid_actions": [
            "decide_coa", "recommend",
        ],
        "completion_criteria": "COA selected, commander's guidance issued.",
    },
    {
        "phase_id": 7,
        "phase_name": "Orders Production",
        "description": "Produce draft OPORD based on the selected COA.",
        "max_rounds": 2,
        "active_roles": ["S3", "S2", "S4", "S6", "FSO", "CIMIC", "ENGR"],
        "primary_role": "S3",
        "valid_actions": [
            "task_organize", "recommend", "concur", "dissent",
            "assess_logistics", "assess_comms",
        ],
        "completion_criteria": "Draft OPORD produced with situation, mission, execution, sustainment, and command/signal paragraphs.",
    },
]


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TacticalAction:
    """A single action taken by an agent during deliberation."""
    phase: int
    phase_name: str
    round: int
    timestamp: str
    agent_id: int
    agent_role: str
    agent_name: str
    action_type: str
    content: str
    references: List[str] = field(default_factory=list)
    confidence: float = 0.5
    risk_assessment: str = "medium"
    addressed_to: str = "ALL"
    intel_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PhaseSummary:
    """Compressed summary of a completed phase."""
    phase_id: int
    phase_name: str
    compressed_text: str
    action_count: int
    key_decisions: List[str] = field(default_factory=list)


@dataclass
class COAProposal:
    """A Course of Action proposed during Phase 3."""
    coa_id: int
    coa_name: str
    description: str
    proposed_by: str
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    dissenting_views: List[str] = field(default_factory=list)


# ============================================================================
# T3.3 — Main Deliberation Engine
# ============================================================================

class TacticalDeliberationEngine:
    """
    Executes the 7-phase MDMP deliberation among tactical staff agents.
    Replaces OASIS simulation entirely.
    """

    def __init__(
        self,
        agents: List[dict],
        config: dict,
        output_dir: str,
        graph_id: str,
    ):
        # Separate staff officers from SME agents
        self.staff_agents = {a["role_code"]: a for a in agents if not a.get("is_sme")}
        self.sme_agents = {a["role_code"]: a for a in agents if a.get("is_sme")}
        # Combined lookup (backwards compatible)
        self.agents = {**self.staff_agents, **self.sme_agents}
        self.config = config
        self.output_dir = output_dir
        self.graph_id = graph_id

        # LLM client
        cfg = Config()
        self.llm_client = AsyncOpenAI(
            api_key=cfg.LLM_API_KEY,
            base_url=cfg.LLM_BASE_URL,
        )
        self.llm_model = cfg.LLM_MODEL_NAME

        # State
        self.deliberation_log: List[TacticalAction] = []
        self.phase_summaries: Dict[int, PhaseSummary] = {}
        self.coas: List[COAProposal] = []
        self.selected_coa: Optional[int] = None
        self.current_phase: int = 0
        self.current_round: int = 0

        # Mission context from config
        mission_cfg = config.get("mission_config", {})
        self.mission_statement = mission_cfg.get("mission_statement", "")
        self.commander_intent = mission_cfg.get("commander_intent", "")
        self.constraints = mission_cfg.get("constraints", [])

        # IPC / state file
        self.state_file = os.path.join(output_dir, "run_state.json")
        self.actions_file = os.path.join(output_dir, "deliberation", "actions.jsonl")

        # Concurrency settings
        cfg_obj = Config()
        self.semaphore = asyncio.Semaphore(cfg_obj.LLM_MAX_CONCURRENT)
        self.parallel_agents = cfg_obj.DELIBERATION_PARALLEL_AGENTS

        # SME settings
        self.sme_enabled = cfg_obj.SME_AGENT_ENABLED and len(self.sme_agents) > 0
        self.sme_volunteer_probability = cfg_obj.SME_VOLUNTEER_PROBABILITY

        # Graceful shutdown
        self._shutdown = False

    async def run(self):
        """Main deliberation loop across all MDMP phases."""
        os.makedirs(os.path.join(self.output_dir, "deliberation"), exist_ok=True)

        phases = self.config.get("phases", MDMP_PHASES)
        total_phases = len(phases)

        logger.info(f"Starting MDMP deliberation with {len(self.agents)} agents, {total_phases} phases")
        self._update_state("running", phase=0, message="Starting deliberation...")

        for phase in phases:
            if self._shutdown:
                break

            self.current_phase = phase["phase_id"]
            phase_name = phase["phase_name"]
            max_rounds = phase.get("max_rounds", 3)
            active_roles = phase.get("active_roles", [])
            valid_actions = phase.get("valid_actions", [])

            logger.info(f"=== Phase {self.current_phase}: {phase_name} ===")
            self._update_state(
                "running",
                phase=self.current_phase,
                phase_name=phase_name,
                message=f"Phase {self.current_phase}: {phase_name}",
            )

            phase_log: List[TacticalAction] = []

            for round_num in range(max_rounds):
                if self._shutdown:
                    break

                self.current_round = round_num + 1
                logger.info(f"  Round {self.current_round}/{max_rounds}")

                # Primary role goes first, then others (staff only)
                primary = phase.get("primary_role", active_roles[0])
                other_roles = [r for r in active_roles if r != primary and r in self.staff_agents]

                if self._shutdown:
                    break

                # ── Step 1: Primary agent acts first (always sequential) ──
                if primary in self.agents:
                    primary_agent = self.agents[primary]
                    primary_ctx = self._build_agent_context(
                        primary_agent, phase, round_num, phase_log
                    )
                    primary_action = await self._agent_act(primary_agent, primary_ctx, valid_actions)
                    await self._process_action(primary_action, primary, phase_name, phase_log)

                # ── Step 2: Remaining agents ──
                if self._shutdown:
                    break

                if self.parallel_agents and len(other_roles) > 1:
                    # Parallel mode: all remaining agents act on a frozen snapshot
                    frozen_log = list(phase_log)

                    async def _act_one(rc: str):
                        ag = self.agents[rc]
                        ctx = self._build_agent_context(ag, phase, round_num, frozen_log)
                        return await self._agent_act(ag, ctx, valid_actions)

                    results = await asyncio.gather(
                        *[_act_one(rc) for rc in other_roles],
                        return_exceptions=True,
                    )

                    # Process results in deterministic order
                    for rc, result in zip(other_roles, results):
                        if isinstance(result, Exception):
                            logger.error(f"Parallel agent {rc} failed: {result}")
                            fallback = TacticalAction(
                                phase=self.current_phase,
                                phase_name=phase_name,
                                round=self.current_round,
                                timestamp=datetime.now().isoformat(),
                                agent_id=self.agents[rc]["agent_id"],
                                agent_role=rc,
                                agent_name=self.agents[rc].get("name", rc),
                                action_type=valid_actions[0] if valid_actions else "recommend",
                                content=f"[Error: agent failed — {str(result)[:100]}]",
                                confidence=0.3,
                                risk_assessment="medium",
                            )
                            await self._process_action(fallback, rc, phase_name, phase_log)
                        else:
                            await self._process_action(result, rc, phase_name, phase_log)
                else:
                    # Sequential mode (original behavior)
                    for role_code in other_roles:
                        if self._shutdown:
                            break
                        agent = self.agents[role_code]
                        context = self._build_agent_context(
                            agent, phase, round_num, phase_log
                        )
                        action = await self._agent_act(agent, context, valid_actions)
                        await self._process_action(action, role_code, phase_name, phase_log)

                # ── Step 3: SME participation (if enabled, phases 1-5 only) ──
                if self.sme_enabled and self.current_phase <= 5 and not self._shutdown:
                    await self._process_sme_round(phase, phase_log)

                # T3.7 — Check phase completion
                if await self._check_phase_completion(phase, phase_log):
                    logger.info(f"  Phase {self.current_phase} completed at round {self.current_round}")
                    break

            # T3.8 — Summarize phase
            summary = await self._summarize_phase(phase, phase_log)
            self.phase_summaries[phase["phase_id"]] = summary

            # T3.9 — Build comparison matrix in Phase 5
            if phase["phase_id"] == 5:
                self._build_comparison_matrix(phase_log)

            # T3.10 — Extract COA decision after Phase 6
            if phase["phase_id"] == 6 and self.selected_coa is not None:
                self._save_coa_decision()

        # ── Phase 8: Social Impact Assessment (optional) ──
        cfg_obj = Config()
        if (cfg_obj.OASIS_FEEDBACK_ENABLED
                and cfg_obj.OASIS_FEEDBACK_RUN_PHASE_8
                and not self._shutdown):
            await self._run_phase_8()

        # Done
        self._update_state(
            "completed",
            phase=self.current_phase,
            message="Deliberation complete",
            coas_proposed=len(self.coas),
            selected_coa=self.selected_coa,
        )
        logger.info("Deliberation complete")

        # Save final results
        self._save_results()

    # ========================================================================
    # T3.3b — Process a single agent action (shared by sequential & parallel)
    # ========================================================================

    async def _process_action(
        self,
        action: 'TacticalAction',
        role_code: str,
        phase_name: str,
        phase_log: List['TacticalAction'],
    ):
        """Append action to logs and handle intel/COA/decision side-effects."""
        # Intel request → query graph
        if action.action_type == "request_intel":
            intel = await self._query_graph(action.content)
            action.intel_response = intel

            intel_action = TacticalAction(
                phase=self.current_phase,
                phase_name=phase_name,
                round=self.current_round,
                timestamp=datetime.now().isoformat(),
                agent_id=action.agent_id,
                agent_role=role_code,
                agent_name=action.agent_name,
                action_type="provide_intel",
                content=f"[Graph Query: {action.content}]\n\nResults:\n{intel}",
                references=action.references,
                confidence=0.9,
                risk_assessment="low",
            )
            phase_log.append(intel_action)
            self.deliberation_log.append(intel_action)
            self._log_action(intel_action)

        # Track COA proposals
        if action.action_type == "propose_coa":
            coa = COAProposal(
                coa_id=len(self.coas) + 1,
                coa_name=f"COA-{len(self.coas) + 1}",
                description=action.content[:500],
                proposed_by=role_code,
            )
            self.coas.append(coa)

        # Track COA decision
        if action.action_type == "decide_coa":
            self.selected_coa = self._extract_coa_selection(action.content)

        phase_log.append(action)
        self.deliberation_log.append(action)
        self._log_action(action)

    # ========================================================================
    # T3.3c — SME Round Processing
    # ========================================================================

    async def _process_sme_round(
        self,
        phase: dict,
        phase_log: List['TacticalAction'],
    ):
        """Process SME participation after staff round.

        1. If any officer used consult_sme → match best SME and respond.
        2. Otherwise → 1-2 SMEs may volunteer testimony (probabilistic).
        """
        phase_id = phase["phase_id"]

        # Find relevant SMEs for this phase
        phase_smes = {
            rc: a for rc, a in self.sme_agents.items()
            if phase_id in a.get("relevant_phases", [])
        }
        if not phase_smes:
            return

        # Check for consult_sme actions from this round
        consult_actions = [
            a for a in phase_log
            if a.action_type == "consult_sme" and a.round == self.current_round
        ]

        if consult_actions:
            # Respond to each consultation
            for consult in consult_actions:
                best_sme = self._match_sme_to_question(consult.content, phase_smes)
                if best_sme:
                    sme_agent = phase_smes[best_sme]
                    ctx = self._build_sme_context(sme_agent, phase, phase_log, consult.content)
                    action = await self._sme_act(sme_agent, ctx)
                    await self._process_action(action, best_sme, phase["phase_name"], phase_log)
                    logger.info(f"  SME {best_sme} responded to consultation from {consult.agent_role}")
        else:
            # Voluntary testimony — probabilistic
            sme_list = list(phase_smes.items())
            random.shuffle(sme_list)
            volunteers = 0
            max_volunteers = min(2, len(sme_list))

            for rc, sme_agent in sme_list:
                if volunteers >= max_volunteers:
                    break
                if random.random() < self.sme_volunteer_probability:
                    ctx = self._build_sme_context(sme_agent, phase, phase_log)
                    action = await self._sme_act(sme_agent, ctx)
                    await self._process_action(action, rc, phase["phase_name"], phase_log)
                    volunteers += 1
                    logger.info(f"  SME {rc} volunteered testimony")

    def _match_sme_to_question(
        self,
        question: str,
        phase_smes: Dict[str, dict],
    ) -> Optional[str]:
        """Match an officer's consult_sme question to the best SME by expertise_tags."""
        question_lower = question.lower()
        best_rc = None
        best_score = 0

        for rc, sme in phase_smes.items():
            score = 0
            tags = sme.get("expertise_tags", [])
            for tag in tags:
                # Check if any word from the tag appears in the question
                for word in tag.split("_"):
                    if len(word) >= 4 and word in question_lower:
                        score += 1
            # Also match on entity name
            name = sme.get("name", "").lower()
            if name and name in question_lower:
                score += 3
            # Match on role_name
            role = sme.get("role_name", "").lower()
            for word in role.split():
                if len(word) >= 4 and word in question_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_rc = rc

        # If no keyword match, just pick the highest credibility SME
        if best_rc is None and phase_smes:
            best_rc = max(phase_smes, key=lambda rc: phase_smes[rc].get("credibility", 0.5))

        return best_rc

    def _build_sme_context(
        self,
        sme_agent: dict,
        phase: dict,
        phase_log: List['TacticalAction'],
        consultation_question: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build prompt context for an SME's turn — non-doctrinal, personal testimony."""
        system = f"""You are {sme_agent.get('name', 'a local expert')}, {sme_agent.get('role_name', 'Subject Matter Expert')}.

{sme_agent.get('persona', '')}

CRITICAL RULES:
- You are NOT a military officer. Do NOT use military jargon, acronyms, or doctrinal frameworks.
- Speak from personal experience and first-hand knowledge ONLY.
- You may express emotions: fear, frustration, hope, anger.
- Be specific about what you have seen, heard, or know from living in the area.
- If asked about something you don't know, say so honestly.
- Your credibility rating: {sme_agent.get('credibility', 0.7):.1f}/1.0"""

        user_parts = []

        user_parts.append(f"## CONTEXT: Military staff are in Phase {phase['phase_id']} — {phase['phase_name']}")

        if consultation_question:
            user_parts.append(f"## QUESTION ASKED BY MILITARY STAFF:\n{consultation_question}")
        else:
            user_parts.append("## You have been invited to share relevant testimony with the military staff.")

        # Recent deliberation context (so SME can respond to what's being discussed)
        if phase_log:
            recent = phase_log[-10:]
            history = "\n---\n".join([
                f"[{a.agent_role}] {a.agent_name}: {a.content[:300]}"
                for a in recent
            ])
            user_parts.append(f"## RECENT DISCUSSION\n{history}")

        user_parts.append("""## INSTRUCTIONS
Provide your testimony or response. Speak naturally as a local civilian.

Respond with ONLY valid JSON:
{
    "action_type": "sme_testimony",
    "content": "your testimony (200-500 words, personal and specific)",
    "references": [],
    "confidence": 0.0-1.0,
    "risk_assessment": "low|medium|high|critical",
    "addressed_to": "ALL or a specific role code"
}""")

        return {
            "system": system,
            "user": "\n\n".join(user_parts),
        }

    async def _sme_act(
        self,
        sme_agent: dict,
        context: Dict[str, str],
    ) -> 'TacticalAction':
        """Call LLM for an SME's testimony."""
        role_code = sme_agent["role_code"]
        valid_actions = ["sme_testimony"]

        async with self.semaphore:
            try:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": context["system"]},
                        {"role": "user", "content": context["user"]},
                    ],
                    temperature=0.8,  # Slightly higher for more natural/varied testimony
                    max_tokens=1500,
                )

                content = response.choices[0].message.content.strip()

                # Strip markdown fences
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                if content.startswith("json"):
                    content = content[4:]

                data = json.loads(content)

            except json.JSONDecodeError:
                data = {
                    "action_type": "sme_testimony",
                    "content": content if 'content' in dir() else "I have information to share.",
                    "confidence": 0.5,
                    "risk_assessment": "medium",
                }
            except Exception as e:
                logger.error(f"SME LLM call failed for {role_code}: {e}")
                data = {
                    "action_type": "sme_testimony",
                    "content": f"[Error: SME call failed — {str(e)[:100]}]",
                    "confidence": 0.3,
                    "risk_assessment": "medium",
                }

        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5

        risk = data.get("risk_assessment", "medium")
        if risk not in ("low", "medium", "high", "critical"):
            risk = "medium"

        return TacticalAction(
            phase=self.current_phase,
            phase_name=MDMP_PHASES[self.current_phase - 1]["phase_name"] if self.current_phase <= len(MDMP_PHASES) else "Unknown",
            round=self.current_round,
            timestamp=datetime.now().isoformat(),
            agent_id=sme_agent["agent_id"],
            agent_role=role_code,
            agent_name=sme_agent.get("name", role_code),
            action_type="sme_testimony",
            content=str(data.get("content", ""))[:2000],
            references=data.get("references", [])[:10],
            confidence=confidence,
            risk_assessment=risk,
            addressed_to=data.get("addressed_to", "ALL"),
        )

    # ========================================================================
    # T3.4 — Build Agent Context (prompt per turn)
    # ========================================================================

    def _build_agent_context(
        self,
        agent: dict,
        phase: dict,
        round_num: int,
        phase_log: List[TacticalAction],
    ) -> Dict[str, str]:
        """Build the full prompt context for an agent's turn."""

        role_code = agent["role_code"]

        # System prompt: agent identity
        system = f"""You are {agent.get('name', role_code)}, {agent['role_name']} on a military staff.

{agent.get('persona', agent.get('description', ''))}

Your cognitive profile:
- Risk tolerance: {agent.get('risk_tolerance', 0.5)} (0=conservative, 1=aggressive)
- Analytical depth: {agent.get('analytical_depth', 0.5)} (0=quick/intuitive, 1=deep/methodical)
- Doctrinal adherence: {agent.get('doctrinal_adherence', 0.5)} (0=creative/flexible, 1=strict doctrine)

Your expertise: maneuver={agent.get('expertise_maneuver', 0.5)}, fires={agent.get('expertise_fires', 0.5)}, logistics={agent.get('expertise_logistics', 0.5)}, intel={agent.get('expertise_intel', 0.5)}, comms={agent.get('expertise_comms', 0.5)}

IMPORTANT: Stay in character. Your analysis should reflect your role, expertise, and cognitive profile. A logistics officer focuses on sustainment; a Red Team member thinks like the adversary."""

        # User prompt: phase context + mission + history + instructions
        user_parts = []

        # Current phase
        user_parts.append(f"""## CURRENT PHASE: Phase {phase['phase_id']} — {phase['phase_name']}
{phase.get('description', phase.get('completion_criteria', ''))}
Your role in this phase: {'LEAD — You set the agenda and drive discussion' if role_code == phase.get('primary_role') else 'CONTRIBUTOR — Provide analysis from your domain expertise'}
Round: {round_num + 1}/{phase.get('max_rounds', 3)}""")

        # Mission summary
        user_parts.append(f"""## MISSION
Statement: {self.mission_statement or '(To be determined during Mission Analysis)'}
Commander's Intent: {self.commander_intent or '(Not yet issued)'}
Constraints: {', '.join(self.constraints) if self.constraints else '(None identified yet)'}""")

        # Entities assigned to this agent (from agent profile)
        entity_info = self._get_entity_info_for_agent(agent)
        if entity_info:
            user_parts.append(f"## ENTITIES UNDER YOUR RESPONSIBILITY\n{entity_info}")

        # COAs if any exist
        if self.coas:
            coa_text = "\n".join([
                f"- COA-{c.coa_id} ({c.coa_name}): {c.description[:200]}... [by {c.proposed_by}]"
                for c in self.coas
            ])
            user_parts.append(f"## COURSES OF ACTION PROPOSED\n{coa_text}")

        # Previous phase summaries (compressed)
        if self.phase_summaries:
            summaries = []
            for pid, s in sorted(self.phase_summaries.items()):
                summaries.append(f"### Phase {pid}: {s.phase_name}\n{s.compressed_text[:500]}")
            user_parts.append(f"## PREVIOUS PHASE SUMMARIES\n" + "\n\n".join(summaries))

        # Current phase deliberation history
        if phase_log:
            history_lines = []
            for a in phase_log[-30:]:  # Last 30 entries max
                prefix = f"[{a.agent_role}] {a.agent_name}"
                action_label = a.action_type.upper().replace("_", " ")
                conf = f"(confidence: {a.confidence:.1f}, risk: {a.risk_assessment})"
                history_lines.append(f"{prefix} — {action_label} {conf}:\n{a.content[:400]}")
            history_text = "\n---\n".join(history_lines)
            user_parts.append(f"## DELIBERATION THIS PHASE (Round {round_num + 1})\n{history_text}")

        # SME availability info
        if self.sme_enabled and phase["phase_id"] <= 5:
            phase_smes = [
                a for a in self.sme_agents.values()
                if phase["phase_id"] in a.get("relevant_phases", [])
            ]
            if phase_smes:
                sme_lines = [
                    f"- {a.get('name', a['role_code'])} ({a.get('role_name', 'SME')}): {a.get('specialty', 'local expert')}"
                    for a in phase_smes
                ]
                user_parts.append(
                    "## AVAILABLE SUBJECT MATTER EXPERTS\n"
                    "You may use 'consult_sme' to request testimony from a local expert:\n"
                    + "\n".join(sme_lines)
                )

        # Instructions
        valid = ", ".join(phase.get("valid_actions", []))
        user_parts.append(f"""## INSTRUCTIONS
Choose ONE action from: [{valid}]

Respond with ONLY valid JSON:
{{
    "action_type": "one of the available actions",
    "content": "your detailed analysis, proposal, or evaluation (be specific and substantive, 200-500 words)",
    "references": [],
    "confidence": 0.0-1.0,
    "risk_assessment": "low|medium|high|critical",
    "addressed_to": "ALL or a specific role code"
}}""")

        return {
            "system": system,
            "user": "\n\n".join(user_parts),
        }

    def _get_entity_info_for_agent(self, agent: dict) -> str:
        """Get entity summaries for an agent from the stored agent data."""
        # Entity info was stored during agent generation — use assigned_entity_uuids
        # For now, return a placeholder that will be populated by the entity reader
        entity_types = agent.get("assigned_entity_types", [])
        if "__ALL__" in entity_types:
            return "(Full battlespace awareness — all entities visible)"
        if entity_types:
            return f"Monitoring entity types: {', '.join(entity_types)}"
        return ""

    # ========================================================================
    # T3.5 — Agent Act (LLM call + parse)
    # ========================================================================

    async def _agent_act(
        self,
        agent: dict,
        context: Dict[str, str],
        valid_actions: List[str],
    ) -> TacticalAction:
        """Call LLM for an agent's action and parse the response."""
        role_code = agent["role_code"]

        async with self.semaphore:
            try:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": context["system"]},
                        {"role": "user", "content": context["user"]},
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                )

                content = response.choices[0].message.content.strip()

                # Strip markdown fences
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                if content.startswith("json"):
                    content = content[4:]

                data = json.loads(content)

            except json.JSONDecodeError:
                logger.warning(f"JSON parse failed for {role_code}, using raw content")
                data = {
                    "action_type": valid_actions[0] if valid_actions else "recommend",
                    "content": content if 'content' in dir() else "Analysis in progress.",
                    "confidence": 0.5,
                    "risk_assessment": "medium",
                }
            except Exception as e:
                logger.error(f"LLM call failed for {role_code}: {e}")
                data = {
                    "action_type": valid_actions[0] if valid_actions else "recommend",
                    "content": f"[Error: LLM call failed — {str(e)[:100]}]",
                    "confidence": 0.3,
                    "risk_assessment": "medium",
                }

        # Validate action_type
        action_type = data.get("action_type", "recommend")
        if action_type not in valid_actions:
            action_type = valid_actions[0] if valid_actions else "recommend"

        # Validate confidence
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5

        risk = data.get("risk_assessment", "medium")
        if risk not in ("low", "medium", "high", "critical"):
            risk = "medium"

        return TacticalAction(
            phase=self.current_phase,
            phase_name=MDMP_PHASES[self.current_phase - 1]["phase_name"] if self.current_phase <= len(MDMP_PHASES) else "Unknown",
            round=self.current_round,
            timestamp=datetime.now().isoformat(),
            agent_id=agent["agent_id"],
            agent_role=role_code,
            agent_name=agent.get("name", role_code),
            action_type=action_type,
            content=str(data.get("content", ""))[:2000],
            references=data.get("references", [])[:10],
            confidence=confidence,
            risk_assessment=risk,
            addressed_to=data.get("addressed_to", "ALL"),
        )

    # ========================================================================
    # T3.6 — Query Graph via Zep Search
    # ========================================================================

    async def _query_graph(self, query: str) -> str:
        """Query the knowledge graph for intelligence. Uses Graphiti search."""
        try:
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF

            graphiti = get_graphiti()
            results = run_async(graphiti.search_(
                query=query,
                config=EDGE_HYBRID_SEARCH_RRF,
                group_ids=[self.graph_id],
            ))

            facts = []
            if results and hasattr(results, 'edges'):
                for edge in results.edges[:10]:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.append(f"- {edge.fact}")

            if facts:
                return "\n".join(facts[:10])
            else:
                return "(No relevant intelligence found in the knowledge graph for this query)"

        except Exception as e:
            logger.warning(f"Graph query failed: {e}")
            return f"(Graph query error: {str(e)[:100]})"

    # ========================================================================
    # T3.7 — Phase Completion Check
    # ========================================================================

    async def _check_phase_completion(
        self,
        phase: dict,
        phase_log: List[TacticalAction],
    ) -> bool:
        """Check if a phase has met its completion criteria."""
        # Hard limit: if we've had enough actions
        min_actions = len(phase.get("active_roles", [])) * 2
        if len(phase_log) < min_actions:
            return False  # Too early to complete

        # Phase 3: need at least 2 COA proposals
        if phase["phase_id"] == 3 and len(self.coas) < 2:
            return False

        # Phase 6: need a DECIDE_COA action
        if phase["phase_id"] == 6:
            has_decision = any(a.action_type == "decide_coa" for a in phase_log)
            return has_decision

        # For other phases, use LLM moderator
        try:
            summary = "\n".join([
                f"[{a.agent_role}] {a.action_type}: {a.content[:150]}"
                for a in phase_log[-15:]
            ])

            prompt = f"""Evaluate if phase '{phase['phase_name']}' has met its completion criteria.

Criteria: {phase['completion_criteria']}

Recent deliberation:
{summary}

Respond with JSON only: {{"complete": true/false, "reason": "brief explanation"}}"""

            async with self.semaphore:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are a military staff process moderator. Evaluate if deliberation criteria are met. When in doubt, say false — it's better to continue than to stop early."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=200,
                )

            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            if content.startswith("json"):
                content = content[4:]

            result = json.loads(content)
            return result.get("complete", False)

        except Exception as e:
            logger.warning(f"Completion check failed: {e}")
            return False

    # ========================================================================
    # T3.8 — Phase Summarization
    # ========================================================================

    async def _summarize_phase(
        self,
        phase: dict,
        phase_log: List[TacticalAction],
    ) -> PhaseSummary:
        """Compress phase results into a summary for context management."""
        if not phase_log:
            return PhaseSummary(
                phase_id=phase["phase_id"],
                phase_name=phase["phase_name"],
                compressed_text="(No actions taken in this phase)",
                action_count=0,
            )

        full_text = "\n".join([
            f"[{a.agent_role}] {a.action_type}: {a.content[:300]}"
            for a in phase_log
        ])

        try:
            prompt = f"""Summarize the results of phase '{phase['phase_name']}' in max 400 words.

Include:
- Key decisions made
- Points of consensus
- Points of disagreement
- Artifacts produced (COAs, assessments, etc.)
- Intelligence gaps identified

Full deliberation:
{full_text[:6000]}"""

            async with self.semaphore:
                response = await self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": "You are a military staff officer summarizing deliberation results. Be concise and factual."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=600,
                )

            summary_text = response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Phase summary failed: {e}")
            # Fallback: mechanical summary
            action_types = {}
            for a in phase_log:
                action_types[a.action_type] = action_types.get(a.action_type, 0) + 1
            summary_text = f"Phase {phase['phase_id']} ({phase['phase_name']}): {len(phase_log)} actions. Types: {action_types}"

        key_decisions = [
            a.content[:200] for a in phase_log
            if a.action_type in ("decide_coa", "propose_coa", "score_coa", "recommend")
        ]

        return PhaseSummary(
            phase_id=phase["phase_id"],
            phase_name=phase["phase_name"],
            compressed_text=summary_text,
            action_count=len(phase_log),
            key_decisions=key_decisions[:5],
        )

    # ========================================================================
    # T3.9 — COA Comparison Matrix
    # ========================================================================

    def _build_comparison_matrix(self, phase_log: List[TacticalAction]):
        """Build the COA comparison matrix from Phase 5 SCORE_COA actions."""
        criteria = self.config.get("evaluation_criteria", [
            {"name": "Mission Success Probability", "weight": 0.30},
            {"name": "Force Protection", "weight": 0.25},
            {"name": "Time Efficiency", "weight": 0.15},
            {"name": "Sustainability", "weight": 0.15},
            {"name": "Flexibility", "weight": 0.15},
        ])

        # Collect scores from SCORE_COA actions
        for action in phase_log:
            if action.action_type == "score_coa":
                # Try to parse scores from content
                self._parse_and_apply_scores(action, criteria)

        # Calculate totals
        for coa in self.coas:
            total = 0.0
            for criterion in criteria:
                cname = criterion["name"]
                weight = criterion["weight"]
                score = coa.scores.get(cname, 5.0)
                total += score * weight
            coa.total_score = round(total, 2)

        # Sort by score
        self.coas.sort(key=lambda c: c.total_score, reverse=True)

        # Save matrix
        matrix = {
            "criteria": criteria,
            "coas": [
                {
                    "coa_id": c.coa_id,
                    "coa_name": c.coa_name,
                    "description": c.description[:300],
                    "proposed_by": c.proposed_by,
                    "scores": c.scores,
                    "total_score": c.total_score,
                    "dissenting_views": c.dissenting_views,
                }
                for c in self.coas
            ],
            "ranking": [c.coa_id for c in self.coas],
            "recommended_coa": self.coas[0].coa_id if self.coas else None,
        }

        matrix_path = os.path.join(self.output_dir, "deliberation", "coa_matrix.json")
        with open(matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2)

        logger.info(f"COA comparison matrix saved: {[c.coa_id for c in self.coas]}")

    def _parse_and_apply_scores(self, action: TacticalAction, criteria: List[dict]):
        """Try to extract numeric scores from a SCORE_COA action's content."""
        content = action.content.lower()

        for coa in self.coas:
            coa_ref = f"coa-{coa.coa_id}".lower()
            coa_ref2 = f"coa {coa.coa_id}".lower()
            if coa_ref in content or coa_ref2 in content:
                # Try to find scores in the text
                for criterion in criteria:
                    cname = criterion["name"]
                    # Look for patterns like "Mission Success: 7" or "7/10"
                    for keyword in cname.lower().split():
                        if len(keyword) < 4:
                            continue
                        idx = content.find(keyword)
                        if idx != -1:
                            # Look for a number nearby
                            segment = content[idx:idx+60]
                            for word in segment.split():
                                try:
                                    val = float(word.strip(":/,()"))
                                    if 0 <= val <= 10:
                                        coa.scores[cname] = val
                                        break
                                except ValueError:
                                    continue

        # Collect dissenting views
        if action.action_type == "dissent":
            for coa in self.coas:
                if f"coa-{coa.coa_id}" in action.content.lower():
                    coa.dissenting_views.append(
                        f"{action.agent_role}: {action.content[:200]}"
                    )

    def _extract_coa_selection(self, content: str) -> Optional[int]:
        """Extract which COA was selected from a DECIDE_COA action."""
        content_lower = content.lower()
        for coa in self.coas:
            if f"coa-{coa.coa_id}" in content_lower or f"coa {coa.coa_id}" in content_lower:
                return coa.coa_id
        # Default to highest scoring
        if self.coas:
            return self.coas[0].coa_id
        return None

    # ========================================================================
    # T3.10 — COA Extraction (after Phase 6)
    # ========================================================================

    def _save_coa_decision(self):
        """Save selected COA + phase summaries to coa_decision.json for OASIS feedback."""
        selected = None
        for c in self.coas:
            if c.coa_id == self.selected_coa:
                selected = c
                break

        if not selected:
            return

        decision = {
            "selected_coa": {
                "coa_id": selected.coa_id,
                "coa_name": selected.coa_name,
                "description": selected.description,
                "proposed_by": selected.proposed_by,
                "total_score": selected.total_score,
            },
            "commander_intent": self.commander_intent,
            "mission_statement": self.mission_statement,
            "phase_summaries": {
                str(k): {
                    "phase_name": v.phase_name,
                    "summary": v.compressed_text[:500],
                }
                for k, v in self.phase_summaries.items()
            },
            "all_coas": [
                {"coa_id": c.coa_id, "coa_name": c.coa_name, "total_score": c.total_score}
                for c in self.coas
            ],
            "extracted_at": datetime.now().isoformat(),
        }

        path = os.path.join(self.output_dir, "deliberation", "coa_decision.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(decision, f, ensure_ascii=False, indent=2)
        logger.info(f"COA decision saved: COA-{selected.coa_id} ({selected.coa_name})")

    # ========================================================================
    # T3.11 — Phase 8: Social Impact Assessment
    # ========================================================================

    async def _run_phase_8(self):
        """Run Phase 8: Social Impact Assessment based on OASIS feedback summary."""
        # Check if OASIS feedback summary exists
        summary_path = os.path.join(self.output_dir, "oasis_feedback", "summary.json")
        if not os.path.exists(summary_path):
            logger.info("Phase 8 skipped: no OASIS feedback summary found")
            return

        with open(summary_path, "r", encoding="utf-8") as f:
            social_summary = json.load(f)

        logger.info("=== Phase 8: Social Impact Assessment ===")
        self.current_phase = 8

        phase_8 = {
            "phase_id": 8,
            "phase_name": "Social Impact Assessment",
            "description": "Review social reaction to the selected COA and recommend modifications if needed.",
            "max_rounds": 2,
            "active_roles": ["CIMIC", "CDR", "XO", "S2"],
            "primary_role": "CIMIC",
            "valid_actions": ["recommend", "evaluate_risk", "concur", "dissent", "identify_gap"],
            "completion_criteria": "Social impact reviewed, modifications recommended if necessary.",
        }

        self._update_state(
            "running", phase=8, phase_name="Social Impact Assessment",
            message="Phase 8: Social Impact Assessment",
        )

        # Inject social summary as a phase summary
        narrative = social_summary.get("narrative_summary", "No summary available")
        sentiment = social_summary.get("sentiment_distribution", {})
        concerns = social_summary.get("key_concerns", [])

        social_text = (
            f"OASIS Social Simulation Results:\n"
            f"Total posts: {social_summary.get('total_posts', 0)}\n"
            f"Sentiment: positive={sentiment.get('positive', 0)}%, "
            f"neutral={sentiment.get('neutral', 0)}%, "
            f"negative={sentiment.get('negative', 0)}%\n"
            f"Key concerns: {', '.join(concerns[:5])}\n\n"
            f"Narrative summary:\n{narrative}"
        )

        self.phase_summaries[7.5] = PhaseSummary(
            phase_id=8,
            phase_name="OASIS Social Feedback",
            compressed_text=social_text,
            action_count=social_summary.get("total_posts", 0),
        )

        phase_log: List[TacticalAction] = []

        for round_num in range(phase_8["max_rounds"]):
            if self._shutdown:
                break

            self.current_round = round_num + 1
            active_roles = phase_8["active_roles"]
            primary = phase_8["primary_role"]
            valid_actions = phase_8["valid_actions"]

            # Primary (CIMIC)
            if primary in self.staff_agents:
                agent = self.staff_agents[primary]
                ctx = self._build_agent_context(agent, phase_8, round_num, phase_log)
                action = await self._agent_act(agent, ctx, valid_actions)
                await self._process_action(action, primary, phase_8["phase_name"], phase_log)

            # Other roles
            for rc in active_roles:
                if rc == primary or rc not in self.staff_agents:
                    continue
                agent = self.staff_agents[rc]
                ctx = self._build_agent_context(agent, phase_8, round_num, phase_log)
                action = await self._agent_act(agent, ctx, valid_actions)
                await self._process_action(action, rc, phase_8["phase_name"], phase_log)

        # Summarize Phase 8
        summary = await self._summarize_phase(phase_8, phase_log)
        self.phase_summaries[8] = summary
        logger.info("Phase 8 complete")

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _log_action(self, action: TacticalAction):
        """Append action to the JSONL log file."""
        with open(self.actions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(action.to_dict(), ensure_ascii=False) + "\n")

    def _update_state(self, status: str, **kwargs):
        """Update the run state file for monitoring."""
        state = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "total_actions": len(self.deliberation_log),
            "coas_proposed": len(self.coas),
            "selected_coa": self.selected_coa,
            **kwargs,
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update state: {e}")

    def _save_results(self):
        """Save final deliberation results."""
        results = {
            "status": "completed",
            "total_actions": len(self.deliberation_log),
            "phases_completed": len(self.phase_summaries),
            "coas_proposed": len(self.coas),
            "selected_coa": self.selected_coa,
            "phase_summaries": {
                str(k): {
                    "phase_name": v.phase_name,
                    "action_count": v.action_count,
                    "summary": v.compressed_text,
                    "key_decisions": v.key_decisions,
                }
                for k, v in self.phase_summaries.items()
            },
            "coas": [
                {
                    "coa_id": c.coa_id,
                    "coa_name": c.coa_name,
                    "description": c.description,
                    "proposed_by": c.proposed_by,
                    "total_score": c.total_score,
                }
                for c in self.coas
            ],
            "completed_at": datetime.now().isoformat(),
        }

        results_path = os.path.join(self.output_dir, "deliberation", "results.json")
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"Results saved to {results_path}")


# ============================================================================
# Script Entry Point (launched by simulation_runner.py as subprocess)
# ============================================================================

async def main():
    """Entry point when run as subprocess."""
    import argparse

    parser = argparse.ArgumentParser(description="Run tactical deliberation")
    parser.add_argument("--simulation-dir", required=True, help="Path to simulation data directory")
    parser.add_argument("--graph-id", required=True, help="Zep graph ID")
    args = parser.parse_args()

    sim_dir = args.simulation_dir

    # Load agents
    agents_path = os.path.join(sim_dir, "agents.json")
    with open(agents_path, "r", encoding="utf-8") as f:
        agents_data = json.load(f)
    agents = agents_data.get("agents", [])

    # Load config
    config_path = os.path.join(sim_dir, "deliberation_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Create engine
    engine = TacticalDeliberationEngine(
        agents=agents,
        config=config,
        output_dir=sim_dir,
        graph_id=args.graph_id,
    )

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        engine._shutdown = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
