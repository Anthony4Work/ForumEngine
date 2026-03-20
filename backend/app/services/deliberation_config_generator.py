"""
Deliberation Config Generator
Generates configuration for tactical MDMP deliberation from mission documents.
Replaces simulation_config_generator.py for the military domain.

Generates:
- MissionConfig: extracted mission parameters
- Phase configuration: adjusted MDMP phases based on mission type/urgency
- Evaluation criteria: weighted criteria for COA comparison
"""

import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.deliberation_config')


# ============================================================================
# T4.1 — Dataclasses
# ============================================================================

@dataclass
class MissionConfig:
    """Extracted mission parameters from the document."""
    mission_type: str = "offense"           # offense, defense, stability, recon, humanitarian
    mission_statement: str = ""              # Restated mission (Who, What, When, Where, Why)
    commander_intent: str = ""               # Purpose, end state, acceptable risk
    constraints: List[str] = field(default_factory=list)     # ROE, time, political
    key_terrain: List[str] = field(default_factory=list)     # Critical terrain features
    priority_intel_requirements: List[str] = field(default_factory=list)  # PIRs
    urgency: str = "priority"               # routine, priority, immediate, flash
    time_horizon_hours: int = 72            # Planning + execution time

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeliberationPhaseConfig:
    """Configuration for a single MDMP phase."""
    phase_id: int = 0
    phase_name: str = ""
    description: str = ""
    max_rounds: int = 3
    active_roles: List[str] = field(default_factory=list)
    primary_role: str = ""
    valid_actions: List[str] = field(default_factory=list)
    completion_criteria: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationCriterion:
    """A weighted criterion for COA comparison."""
    name: str = ""
    weight: float = 0.2
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SMEConfig:
    """Configuration for SME agent participation."""
    enabled: bool = True
    count: int = 5
    volunteer_probability: float = 0.4

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OASISFeedbackConfig:
    """Configuration for OASIS social feedback loop."""
    enabled: bool = False
    rounds: int = 30
    platform: str = "reddit"
    run_phase_8: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeliberationParameters:
    """Complete deliberation configuration."""
    simulation_id: str = ""
    project_id: str = ""
    graph_id: str = ""
    mission_config: MissionConfig = field(default_factory=MissionConfig)
    phases: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_criteria: List[Dict[str, Any]] = field(default_factory=list)
    max_coas: int = 4
    wargame_depth: int = 3
    sme_config: SMEConfig = field(default_factory=SMEConfig)
    oasis_feedback: OASISFeedbackConfig = field(default_factory=OASISFeedbackConfig)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ============================================================================
# Default Evaluation Criteria by Mission Type
# ============================================================================

CRITERIA_BY_MISSION_TYPE = {
    "offense": [
        {"name": "Mission Success Probability", "weight": 0.30, "description": "Likelihood of achieving the objective"},
        {"name": "Force Protection", "weight": 0.25, "description": "Minimizing friendly casualties"},
        {"name": "Time Efficiency", "weight": 0.20, "description": "Speed of execution"},
        {"name": "Sustainability", "weight": 0.15, "description": "Logistics feasibility over the operation"},
        {"name": "Flexibility", "weight": 0.10, "description": "Ability to adapt to changing conditions"},
    ],
    "defense": [
        {"name": "Defensive Strength", "weight": 0.30, "description": "Ability to hold key terrain"},
        {"name": "Force Protection", "weight": 0.25, "description": "Minimizing friendly casualties"},
        {"name": "Depth and Flexibility", "weight": 0.20, "description": "Ability to absorb and counter enemy attack"},
        {"name": "Sustainability", "weight": 0.15, "description": "Logistics feasibility for sustained defense"},
        {"name": "Counterattack Capability", "weight": 0.10, "description": "Ability to transition to offense"},
    ],
    "stability": [
        {"name": "Civilian Impact", "weight": 0.30, "description": "Minimizing harm to civilian population"},
        {"name": "Mission Success", "weight": 0.25, "description": "Achieving stability objectives"},
        {"name": "Force Protection", "weight": 0.20, "description": "Minimizing friendly casualties"},
        {"name": "Local Support", "weight": 0.15, "description": "Gaining local population trust"},
        {"name": "Sustainability", "weight": 0.10, "description": "Long-term feasibility"},
    ],
    "recon": [
        {"name": "Intelligence Gain", "weight": 0.30, "description": "Quality and completeness of information gathered"},
        {"name": "Stealth/Survivability", "weight": 0.25, "description": "Avoiding detection and engagement"},
        {"name": "Time Efficiency", "weight": 0.20, "description": "Speed of reconnaissance"},
        {"name": "Coverage", "weight": 0.15, "description": "Area and targets covered"},
        {"name": "Force Protection", "weight": 0.10, "description": "Minimizing friendly casualties"},
    ],
    "humanitarian": [
        {"name": "Civilian Welfare", "weight": 0.35, "description": "Positive impact on affected population"},
        {"name": "Speed of Response", "weight": 0.25, "description": "Time to deliver assistance"},
        {"name": "Coverage", "weight": 0.20, "description": "Number of people reached"},
        {"name": "Force Protection", "weight": 0.10, "description": "Security of relief operations"},
        {"name": "Sustainability", "weight": 0.10, "description": "Long-term viability of aid delivery"},
    ],
}


# ============================================================================
# T4.2 — Mission Config Extraction via LLM
# ============================================================================

MISSION_EXTRACTION_PROMPT = """Analyze the following mission document and extract operational configuration.

Document (first 10,000 characters):
{document_text}

Analysis requirement from user:
{analysis_requirement}

Extract the following as JSON:
{{
    "mission_type": "offense|defense|stability|recon|humanitarian",
    "mission_statement": "Restated mission in standard format: (Who) (What) (When) (Where) (Why)",
    "commander_intent": "Commander's intent: purpose, end state, acceptable risks",
    "constraints": ["constraint 1", "constraint 2", ...],
    "key_terrain": ["key terrain 1", "key terrain 2", ...],
    "priority_intel_requirements": ["PIR 1", "PIR 2", "PIR 3", ...],
    "urgency": "routine|priority|immediate|flash",
    "time_horizon_hours": 24-720,
    "reasoning": "Brief explanation of how the mission was classified"
}}

Rules:
- mission_statement should be clear and actionable
- constraints must include ROE if mentioned in the document
- PIRs must be specific questions, not generic statements
- time_horizon_hours should reflect realistic planning + execution time
- If the document doesn't contain explicit military content, infer the closest tactical interpretation"""


class DeliberationConfigGenerator:
    """
    Generates deliberation configuration from mission documents.
    Replaces SimulationConfigGenerator for the military domain.
    """

    def __init__(self, openai_client: Optional[OpenAI] = None):
        config = Config()
        self.openai_client = openai_client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.llm_model = config.LLM_MODEL_NAME

    def generate_full_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        document_text: str,
        analysis_requirement: str,
        progress_callback: Optional[Callable] = None,
    ) -> DeliberationParameters:
        """
        Generate complete deliberation configuration.

        Args:
            simulation_id: Simulation instance ID.
            project_id: Project ID.
            graph_id: Zep graph ID.
            document_text: Combined document text.
            analysis_requirement: User's analysis requirement.
            progress_callback: Optional callback(progress_pct, message).

        Returns:
            Complete DeliberationParameters.
        """
        logger.info("Generating deliberation configuration...")

        # Step 1: Extract mission config
        if progress_callback:
            progress_callback(10, "Extracting mission parameters from document...")

        mission_config = self._extract_mission_config(document_text, analysis_requirement)

        # Step 2: Adjust phases based on mission type and urgency
        if progress_callback:
            progress_callback(40, "Configuring MDMP phases...")

        phases = self._configure_phases(mission_config)

        # Step 3: Generate evaluation criteria
        if progress_callback:
            progress_callback(60, "Generating evaluation criteria...")

        criteria = self._generate_criteria(mission_config)

        # Step 4: Determine deliberation depth
        if progress_callback:
            progress_callback(80, "Finalizing configuration...")

        max_coas = 3 if mission_config.urgency == "flash" else 4
        wargame_depth = 2 if mission_config.urgency in ("immediate", "flash") else 3

        # SME and OASIS feedback config from environment
        config = Config()
        sme_cfg = SMEConfig(
            enabled=config.SME_AGENT_ENABLED,
            count=config.SME_AGENT_COUNT,
            volunteer_probability=config.SME_VOLUNTEER_PROBABILITY,
        )
        oasis_cfg = OASISFeedbackConfig(
            enabled=config.OASIS_FEEDBACK_ENABLED,
            rounds=config.OASIS_FEEDBACK_ROUNDS,
            platform=config.OASIS_FEEDBACK_PLATFORM,
            run_phase_8=config.OASIS_FEEDBACK_RUN_PHASE_8,
        )

        params = DeliberationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            mission_config=mission_config,
            phases=phases,
            evaluation_criteria=criteria,
            max_coas=max_coas,
            wargame_depth=wargame_depth,
            sme_config=sme_cfg,
            oasis_feedback=oasis_cfg,
        )

        if progress_callback:
            progress_callback(100, "Configuration complete")

        logger.info(f"Config generated: type={mission_config.mission_type}, urgency={mission_config.urgency}, phases={len(phases)}")
        return params

    def _extract_mission_config(
        self,
        document_text: str,
        analysis_requirement: str,
    ) -> MissionConfig:
        """Extract mission parameters from document using LLM."""
        try:
            prompt = MISSION_EXTRACTION_PROMPT.format(
                document_text=document_text[:10000],
                analysis_requirement=analysis_requirement[:2000],
            )

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a military staff officer extracting mission parameters from operational documents. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
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

            return MissionConfig(
                mission_type=data.get("mission_type", "offense"),
                mission_statement=data.get("mission_statement", ""),
                commander_intent=data.get("commander_intent", ""),
                constraints=data.get("constraints", []),
                key_terrain=data.get("key_terrain", []),
                priority_intel_requirements=data.get("priority_intel_requirements", []),
                urgency=data.get("urgency", "priority"),
                time_horizon_hours=data.get("time_horizon_hours", 72),
            )

        except Exception as e:
            logger.warning(f"Mission config extraction failed: {e}")
            return MissionConfig(
                mission_type="offense",
                mission_statement="(Could not extract — manual input required)",
                urgency="priority",
            )

    # ========================================================================
    # T4.3 — Phase Configuration Based on Mission Type
    # ========================================================================

    def _configure_phases(self, mission_config: MissionConfig) -> List[Dict[str, Any]]:
        """Adjust MDMP phase parameters based on mission type and urgency."""
        phases = self._get_default_phases()

        # Adjust rounds based on urgency
        urgency_multipliers = {
            "routine": 1.0,
            "priority": 0.8,
            "immediate": 0.6,
            "flash": 0.4,
        }
        mult = urgency_multipliers.get(mission_config.urgency, 0.8)

        for phase in phases:
            base_rounds = phase.get("max_rounds", 3)
            phase["max_rounds"] = max(1, round(base_rounds * mult))

        # Mission-type specific adjustments
        if mission_config.mission_type == "defense":
            # More time on IPB (understanding enemy approach)
            for p in phases:
                if p["phase_id"] == 2:
                    p["max_rounds"] = max(p["max_rounds"], 3)

        elif mission_config.mission_type == "recon":
            # Less time on wargaming, more on intel
            for p in phases:
                if p["phase_id"] == 2:
                    p["max_rounds"] = max(p["max_rounds"], 3)
                if p["phase_id"] == 4:
                    p["max_rounds"] = min(p["max_rounds"], 2)

        elif mission_config.mission_type == "humanitarian":
            # CIMIC more prominent, RED less
            for p in phases:
                if p["phase_id"] == 4:  # Wargaming
                    p["max_rounds"] = min(p["max_rounds"], 2)
                if "CIMIC" not in p.get("active_roles", []):
                    p["active_roles"] = p.get("active_roles", []) + ["CIMIC"]

        return phases

    def _get_default_phases(self) -> List[Dict[str, Any]]:
        """Fallback phase definitions if import fails."""
        return [
            {"phase_id": 1, "phase_name": "Mission Analysis", "max_rounds": 3,
             "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"],
             "primary_role": "XO", "valid_actions": ["analyze_terrain", "assess_threat", "assess_logistics", "assess_comms", "identify_key_terrain", "request_intel", "identify_gap", "concur", "dissent"],
             "completion_criteria": "Mission restated, tasks identified, constraints listed."},
            {"phase_id": 2, "phase_name": "Intelligence Preparation (IPB)", "max_rounds": 3,
             "active_roles": ["S2", "CDR", "S3", "RED", "ENGR"], "primary_role": "S2",
             "valid_actions": ["assess_threat", "analyze_terrain", "identify_key_terrain", "request_intel", "provide_intel", "identify_gap", "wargame_counter"],
             "completion_criteria": "Threat assessment complete, enemy COA developed."},
            {"phase_id": 3, "phase_name": "COA Development", "max_rounds": 5,
             "active_roles": ["S3", "CDR", "XO", "S2", "S4", "FSO", "ENGR", "CIMIC"], "primary_role": "S3",
             "valid_actions": ["propose_coa", "refine_coa", "assess_logistics", "evaluate_risk", "request_intel", "dissent", "recommend", "task_organize"],
             "completion_criteria": "2-4 distinct COAs developed."},
            {"phase_id": 4, "phase_name": "COA Analysis (Wargaming)", "max_rounds": 5,
             "active_roles": ["RED", "S3", "S2", "FSO", "S4", "ENGR", "S6"], "primary_role": "RED",
             "valid_actions": ["wargame_move", "wargame_counter", "evaluate_risk", "challenge_assumption", "request_intel", "identify_gap"],
             "completion_criteria": "Each COA wargamed, risks catalogued."},
            {"phase_id": 5, "phase_name": "COA Comparison", "max_rounds": 3,
             "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"], "primary_role": "XO",
             "valid_actions": ["score_coa", "evaluate_risk", "concur", "dissent", "recommend"],
             "completion_criteria": "All COAs scored, matrix complete."},
            {"phase_id": 6, "phase_name": "COA Decision", "max_rounds": 2,
             "active_roles": ["CDR", "XO"], "primary_role": "CDR",
             "valid_actions": ["decide_coa", "recommend"],
             "completion_criteria": "COA selected, guidance issued."},
            {"phase_id": 7, "phase_name": "Orders Production", "max_rounds": 2,
             "active_roles": ["S3", "S2", "S4", "S6", "FSO", "CIMIC", "ENGR"], "primary_role": "S3",
             "valid_actions": ["task_organize", "recommend", "concur", "dissent", "assess_logistics", "assess_comms"],
             "completion_criteria": "Draft OPORD produced."},
        ]

    # ========================================================================
    # T4.4 — Evaluation Criteria Generation
    # ========================================================================

    def _generate_criteria(self, mission_config: MissionConfig) -> List[Dict[str, Any]]:
        """Generate evaluation criteria based on mission type."""
        mission_type = mission_config.mission_type

        if mission_type in CRITERIA_BY_MISSION_TYPE:
            return CRITERIA_BY_MISSION_TYPE[mission_type]

        # Default: balanced criteria
        return CRITERIA_BY_MISSION_TYPE["offense"]

    # ========================================================================
    # T4.5 — Serialization
    # ========================================================================

    @staticmethod
    def save_config(params: DeliberationParameters, output_path: str):
        """Save deliberation config to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(params.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Deliberation config saved to {output_path}")

    @staticmethod
    def load_config(input_path: str) -> Dict[str, Any]:
        """Load deliberation config from JSON file."""
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)
