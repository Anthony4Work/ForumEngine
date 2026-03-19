"""
Tactical Agent Generator
Generates a fixed staff of ~10 tactical agents (military staff officers) that will
participate in MDMP deliberation. Unlike the social media profile generator, agents
here are defined by doctrinal roles, not by graph entities.

Graph entities become the DATA that agents reason about, not agents themselves.
"""

import json
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from openai import OpenAI
from ..config import Config
from ..utils.graphiti_client import get_graphiti
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, EntityReader

logger = get_logger('mirofish.tactical_agents')


# ============================================================================
# T2.1 — Data Model
# ============================================================================

@dataclass
class TacticalAgentProfile:
    """Profile for a tactical staff officer agent."""

    agent_id: int
    role_code: str               # "CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"
    role_name: str               # "Commander", "Intelligence Officer", etc.
    name: str                    # Generated name, e.g. "COL James Mitchell"
    rank: str                    # "COL", "LTC", "MAJ", "CPT"
    specialty: str               # "Intelligence", "Operations", "Logistics", etc.
    persona: str                 # ~2000 char detailed background

    # Cognitive profile (0.0-1.0)
    risk_tolerance: float = 0.5
    analytical_depth: float = 0.5
    doctrinal_adherence: float = 0.5

    # Domain expertise (0.0-1.0)
    expertise_maneuver: float = 0.5
    expertise_fires: float = 0.5
    expertise_logistics: float = 0.5
    expertise_intel: float = 0.5
    expertise_comms: float = 0.5

    # Graph entity mapping
    assigned_entity_uuids: List[str] = field(default_factory=list)
    assigned_entity_types: List[str] = field(default_factory=list)
    source_entity_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TacticalAgentProfile':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# T2.2 — Staff Roles Table (Doctrinal, fixed)
# ============================================================================

STAFF_ROLES = [
    {
        "agent_id": 0,
        "role_code": "CDR",
        "role_name": "Commander",
        "rank": "COL",
        "specialty": "Command",
        "assigned_entity_types": ["__ALL__"],  # CDR sees everything
        "phase_lead": [6],  # Leads Phase 6: COA Decision
        "description": "Senior decision-maker. Weighs all inputs, issues commander's intent, selects COA.",
        # Default cognitive profile
        "default_risk_tolerance": 0.5,
        "default_analytical_depth": 0.7,
        "default_doctrinal_adherence": 0.6,
        "default_expertise": {"maneuver": 0.6, "fires": 0.6, "logistics": 0.6, "intel": 0.6, "comms": 0.6},
    },
    {
        "agent_id": 1,
        "role_code": "XO",
        "role_name": "Executive Officer",
        "rank": "LTC",
        "specialty": "Coordination",
        "assigned_entity_types": ["__ALL__"],  # XO coordinates across all
        "phase_lead": [5],  # Leads Phase 5: COA Comparison
        "description": "Coordinates staff work, challenges assumptions, manages the MDMP timeline.",
        "default_risk_tolerance": 0.4,
        "default_analytical_depth": 0.8,
        "default_doctrinal_adherence": 0.7,
        "default_expertise": {"maneuver": 0.6, "fires": 0.5, "logistics": 0.6, "intel": 0.5, "comms": 0.5},
    },
    {
        "agent_id": 2,
        "role_code": "S2",
        "role_name": "Intelligence Officer",
        "rank": "MAJ",
        "specialty": "Intelligence",
        "assigned_entity_types": ["Threat", "TerrainFeature", "CivilianEntity"],
        "phase_lead": [2],  # Leads Phase 2: IPB
        "description": "Analyzes enemy capabilities, terrain, weather. Develops enemy COAs and threat assessment.",
        "default_risk_tolerance": 0.3,
        "default_analytical_depth": 0.9,
        "default_doctrinal_adherence": 0.5,
        "default_expertise": {"maneuver": 0.4, "fires": 0.3, "logistics": 0.2, "intel": 0.95, "comms": 0.4},
    },
    {
        "agent_id": 3,
        "role_code": "S3",
        "role_name": "Operations Officer",
        "rank": "MAJ",
        "specialty": "Operations",
        "assigned_entity_types": ["MilitaryUnit", "Objective", "Route"],
        "phase_lead": [3, 7],  # Leads Phase 3: COA Dev, Phase 7: Orders
        "description": "Plans maneuver, synchronizes actions, develops friendly COAs, produces operations orders.",
        "default_risk_tolerance": 0.6,
        "default_analytical_depth": 0.7,
        "default_doctrinal_adherence": 0.6,
        "default_expertise": {"maneuver": 0.9, "fires": 0.7, "logistics": 0.4, "intel": 0.5, "comms": 0.5},
    },
    {
        "agent_id": 4,
        "role_code": "S4",
        "role_name": "Logistics Officer",
        "rank": "MAJ",
        "specialty": "Logistics",
        "assigned_entity_types": ["SupplyPoint", "Asset"],
        "phase_lead": [],
        "description": "Evaluates sustainment, supply routes, medical capability, maintenance. Assesses COA feasibility.",
        "default_risk_tolerance": 0.2,
        "default_analytical_depth": 0.8,
        "default_doctrinal_adherence": 0.8,
        "default_expertise": {"maneuver": 0.3, "fires": 0.2, "logistics": 0.95, "intel": 0.2, "comms": 0.5},
    },
    {
        "agent_id": 5,
        "role_code": "S6",
        "role_name": "Communications Officer",
        "rank": "CPT",
        "specialty": "Communications",
        "assigned_entity_types": ["Asset"],
        "phase_lead": [],
        "description": "Evaluates C2 networks, signal redundancy, electronic warfare vulnerabilities.",
        "default_risk_tolerance": 0.3,
        "default_analytical_depth": 0.7,
        "default_doctrinal_adherence": 0.7,
        "default_expertise": {"maneuver": 0.3, "fires": 0.2, "logistics": 0.3, "intel": 0.5, "comms": 0.95},
    },
    {
        "agent_id": 6,
        "role_code": "FSO",
        "role_name": "Fire Support Officer",
        "rank": "MAJ",
        "specialty": "Fires",
        "assigned_entity_types": ["Asset", "Location"],
        "phase_lead": [],
        "description": "Plans fire support, coordinates CAS, assesses collateral damage, synchronizes lethal effects.",
        "default_risk_tolerance": 0.5,
        "default_analytical_depth": 0.6,
        "default_doctrinal_adherence": 0.7,
        "default_expertise": {"maneuver": 0.5, "fires": 0.95, "logistics": 0.3, "intel": 0.4, "comms": 0.4},
    },
    {
        "agent_id": 7,
        "role_code": "RED",
        "role_name": "Red Team (Adversary)",
        "rank": "LTC",
        "specialty": "Adversary Thinking",
        "assigned_entity_types": ["Threat", "MilitaryUnit"],
        "phase_lead": [4],  # Leads Phase 4: Wargaming
        "description": "Thinks like the enemy. Challenges friendly COAs, proposes enemy COAs, identifies vulnerabilities.",
        "default_risk_tolerance": 0.8,
        "default_analytical_depth": 0.9,
        "default_doctrinal_adherence": 0.3,
        "default_expertise": {"maneuver": 0.8, "fires": 0.6, "logistics": 0.4, "intel": 0.8, "comms": 0.4},
    },
    {
        "agent_id": 8,
        "role_code": "CIMIC",
        "role_name": "Civil-Military Coordination Officer",
        "rank": "CPT",
        "specialty": "Civil Affairs",
        "assigned_entity_types": ["CivilianEntity", "Location"],
        "phase_lead": [],
        "description": "Assesses civilian impact, ROE constraints, NGO coordination, population-centric considerations.",
        "default_risk_tolerance": 0.3,
        "default_analytical_depth": 0.7,
        "default_doctrinal_adherence": 0.5,
        "default_expertise": {"maneuver": 0.3, "fires": 0.2, "logistics": 0.4, "intel": 0.6, "comms": 0.4},
    },
    {
        "agent_id": 9,
        "role_code": "ENGR",
        "role_name": "Engineer Officer",
        "rank": "CPT",
        "specialty": "Engineering",
        "assigned_entity_types": ["TerrainFeature", "Route", "Threat"],
        "phase_lead": [],
        "description": "Evaluates mobility/counter-mobility, obstacle clearance, route improvement, counter-IED operations.",
        "default_risk_tolerance": 0.4,
        "default_analytical_depth": 0.8,
        "default_doctrinal_adherence": 0.7,
        "default_expertise": {"maneuver": 0.7, "fires": 0.3, "logistics": 0.6, "intel": 0.4, "comms": 0.3},
    },
]


# ============================================================================
# T2.3 — Entity-to-Agent Assignment
# ============================================================================

def assign_entities_to_agents(
    entities: List[EntityNode],
    roles: List[dict] = None
) -> Dict[str, List[str]]:
    """
    Assign graph entities to staff officers based on entity type.

    Args:
        entities: Filtered entities from the knowledge graph.
        roles: Staff role definitions (defaults to STAFF_ROLES).

    Returns:
        Dict mapping role_code -> list of entity UUIDs.
    """
    if roles is None:
        roles = STAFF_ROLES

    assignments: Dict[str, List[str]] = {role["role_code"]: [] for role in roles}

    for entity in entities:
        entity_type = _get_entity_type(entity)

        assigned_to_any = False
        for role in roles:
            role_types = role["assigned_entity_types"]

            if "__ALL__" in role_types:
                assignments[role["role_code"]].append(entity.uuid)
                assigned_to_any = True
            elif entity_type in role_types:
                assignments[role["role_code"]].append(entity.uuid)
                assigned_to_any = True

        # Fallback: unassigned entities go to CDR
        if not assigned_to_any:
            assignments["CDR"].append(entity.uuid)

    return assignments


def _get_entity_type(entity: EntityNode) -> str:
    """Extract the primary custom type from an entity's labels."""
    generic_labels = {"Entity", "Node"}
    for label in entity.labels:
        if label not in generic_labels:
            return label
    return "Unknown"


# ============================================================================
# T2.4 — LLM-based Persona Generation
# ============================================================================

PERSONA_SYSTEM_PROMPT = """You are generating a detailed persona for a military staff officer in a tactical decision-making simulation. The persona should be realistic, professional, and doctrinally grounded.

You must respond with valid JSON only. No other text."""

PERSONA_USER_TEMPLATE = """Generate a detailed persona for the following military staff officer:

Role: {role_name} ({role_code})
Rank: {rank}
Specialty: {specialty}
Role Description: {description}

Mission Context:
{mission_context}

Entities under this officer's responsibility:
{entity_summaries}

Generate a JSON response with these fields:
1. "name": Full name with rank prefix (e.g. "COL James Mitchell"). Use realistic Western military names.
2. "persona": Detailed background (1500-2000 chars) including:
   - Professional background (20+ year career, previous deployments)
   - Analysis style (how they evaluate situations, what they prioritize)
   - Known biases (e.g., S4 tends to be conservative with resources)
   - Relationship with other staff roles (e.g., S2 and S3 have creative tension)
   - Experience relevant to the current mission type
3. "risk_tolerance": 0.0-1.0 (must align with role expectations)
4. "analytical_depth": 0.0-1.0
5. "doctrinal_adherence": 0.0-1.0
6. "expertise_maneuver": 0.0-1.0
7. "expertise_fires": 0.0-1.0
8. "expertise_logistics": 0.0-1.0
9. "expertise_intel": 0.0-1.0
10. "expertise_comms": 0.0-1.0

Role-specific guidance:
- CDR: moderate risk tolerance (0.4-0.6), balanced expertise
- RED Team: high risk tolerance (0.7-0.9), low doctrinal adherence (0.2-0.4)
- S4: low risk tolerance (0.1-0.3), very high logistics expertise (0.8-1.0)
- S2: low risk tolerance (0.2-0.4), very high intel expertise (0.8-1.0)
- S3: moderate-high risk tolerance (0.5-0.7), very high maneuver expertise (0.8-1.0)
- FSO: moderate risk tolerance, very high fires expertise (0.8-1.0)
- ENGR: moderate risk tolerance, high maneuver + logistics"""


class TacticalAgentGenerator:
    """
    Generates tactical staff officer agents for MDMP deliberation.
    Replaces OasisProfileGenerator for the military domain.
    """

    def __init__(
        self,
        openai_client: Optional[OpenAI] = None,
    ):
        config = Config()
        self.graphiti = get_graphiti()
        self.openai_client = openai_client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.llm_model = config.LLM_MODEL_NAME
        self.entity_reader: Optional[EntityReader] = None

    def generate_all_agents(
        self,
        graph_id: str,
        mission_context: str,
        use_llm: bool = True,
        entity_types: Optional[List[str]] = None,
        progress_callback=None,
    ) -> List[TacticalAgentProfile]:
        """
        Generate all 10 tactical staff agents.

        Args:
            graph_id: Zep graph ID containing mission entities.
            mission_context: Mission analysis requirement text.
            use_llm: Whether to use LLM for persona generation (False = rule-based).
            entity_types: Optional filter for entity types to consider.
            progress_callback: Optional callback(progress_pct, message).

        Returns:
            List of 10 TacticalAgentProfile instances.
        """
        logger.info(f"Generating tactical agents for graph {graph_id}")

        # Step 1: Read entities from graph
        if progress_callback:
            progress_callback(5, "Reading entities from knowledge graph...")

        self.entity_reader = EntityReader()
        filtered = self.entity_reader.filter_defined_entities(graph_id=graph_id)
        entities = filtered.entities if hasattr(filtered, 'entities') else filtered.get("entities", [])
        logger.info(f"Found {len(entities)} filtered entities in graph")

        # Step 2: Assign entities to roles
        if progress_callback:
            progress_callback(15, "Assigning entities to staff roles...")

        assignments = assign_entities_to_agents(entities)

        # Build entity lookup for summaries
        entity_lookup = {e.uuid: e for e in entities}

        # Step 3: Generate agent profiles
        agents = []
        for i, role in enumerate(STAFF_ROLES):
            role_code = role["role_code"]
            assigned_uuids = assignments.get(role_code, [])

            pct = 20 + int((i / len(STAFF_ROLES)) * 70)
            if progress_callback:
                progress_callback(pct, f"Generating agent: {role['role_name']} ({role_code})...")

            # Build entity summaries for this agent
            entity_summaries = self._build_entity_summaries(assigned_uuids, entity_lookup)

            if use_llm:
                profile = self._generate_with_llm(role, mission_context, entity_summaries, assigned_uuids)
            else:
                profile = None

            if profile is None:
                # Fallback to rule-based
                profile = self._generate_rule_based(role, assigned_uuids)

            agents.append(profile)

        if progress_callback:
            progress_callback(95, "Finalizing agent profiles...")

        logger.info(f"Generated {len(agents)} tactical agents")
        return agents

    def _build_entity_summaries(
        self,
        uuids: List[str],
        entity_lookup: Dict[str, EntityNode],
        max_entities: int = 20,
        max_chars_per_entity: int = 200
    ) -> str:
        """Build a text summary of entities assigned to an agent."""
        lines = []
        for uuid in uuids[:max_entities]:
            entity = entity_lookup.get(uuid)
            if entity:
                entity_type = _get_entity_type(entity)
                summary = (entity.summary or "")[:max_chars_per_entity]
                lines.append(f"- [{entity_type}] {entity.name}: {summary}")

        if not lines:
            return "(No specific entities assigned — general oversight role)"

        result = "\n".join(lines)
        if len(uuids) > max_entities:
            result += f"\n... and {len(uuids) - max_entities} more entities"
        return result

    def _generate_with_llm(
        self,
        role: dict,
        mission_context: str,
        entity_summaries: str,
        assigned_uuids: List[str],
    ) -> Optional[TacticalAgentProfile]:
        """Generate an agent profile using LLM."""
        try:
            user_msg = PERSONA_USER_TEMPLATE.format(
                role_name=role["role_name"],
                role_code=role["role_code"],
                rank=role["rank"],
                specialty=role["specialty"],
                description=role["description"],
                mission_context=mission_context[:3000],
                entity_summaries=entity_summaries[:3000],
            )

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            content = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            if content.startswith("json"):
                content = content[4:]

            data = json.loads(content)

            return TacticalAgentProfile(
                agent_id=role["agent_id"],
                role_code=role["role_code"],
                role_name=role["role_name"],
                name=data.get("name", f"{role['rank']} {role['role_name']}"),
                rank=role["rank"],
                specialty=role["specialty"],
                persona=str(data.get("persona", "")).replace("\n", " "),
                risk_tolerance=self._clamp(data.get("risk_tolerance", role["default_risk_tolerance"])),
                analytical_depth=self._clamp(data.get("analytical_depth", role["default_analytical_depth"])),
                doctrinal_adherence=self._clamp(data.get("doctrinal_adherence", role["default_doctrinal_adherence"])),
                expertise_maneuver=self._clamp(data.get("expertise_maneuver", role["default_expertise"]["maneuver"])),
                expertise_fires=self._clamp(data.get("expertise_fires", role["default_expertise"]["fires"])),
                expertise_logistics=self._clamp(data.get("expertise_logistics", role["default_expertise"]["logistics"])),
                expertise_intel=self._clamp(data.get("expertise_intel", role["default_expertise"]["intel"])),
                expertise_comms=self._clamp(data.get("expertise_comms", role["default_expertise"]["comms"])),
                assigned_entity_uuids=assigned_uuids,
                assigned_entity_types=role["assigned_entity_types"],
            )

        except Exception as e:
            logger.warning(f"LLM persona generation failed for {role['role_code']}: {e}")
            return None

    # ============================================================================
    # T2.5 — Rule-based Fallback
    # ============================================================================

    # Name pools for fallback generation
    _FIRST_NAMES = [
        "James", "Sarah", "Michael", "Elena", "David", "Maria", "Robert", "Anna",
        "William", "Catherine", "Thomas", "Patricia", "Richard", "Jennifer", "Daniel", "Lisa",
        "Christopher", "Margaret", "Andrew", "Rebecca", "Joseph", "Laura",
    ]
    _LAST_NAMES = [
        "Mitchell", "Rodriguez", "Thompson", "Chen", "Black", "O'Brien", "Petrov",
        "Kim", "Nakamura", "Weber", "Santos", "Andersen", "Morales", "Singh",
        "Harrison", "Cooper", "Reynolds", "Franklin", "Okafor", "Reyes",
    ]

    def _generate_rule_based(
        self,
        role: dict,
        assigned_uuids: List[str],
    ) -> TacticalAgentProfile:
        """Generate a profile using predefined rules (no LLM call)."""
        first = random.choice(self._FIRST_NAMES)
        last = random.choice(self._LAST_NAMES)
        name = f"{role['rank']} {first} {last}"

        defaults = role["default_expertise"]

        persona = (
            f"{name} is the {role['role_name']} ({role['role_code']}) on the staff. "
            f"Specialty: {role['specialty']}. "
            f"{role['description']} "
            f"With over 20 years of military service and multiple deployments, "
            f"{first} brings deep expertise in {role['specialty'].lower()} operations. "
            f"Known for a {'methodical' if role['default_analytical_depth'] > 0.7 else 'pragmatic'} "
            f"approach to problem-solving and a "
            f"{'conservative' if role['default_risk_tolerance'] < 0.4 else 'balanced' if role['default_risk_tolerance'] < 0.6 else 'aggressive'} "
            f"attitude toward risk."
        )

        return TacticalAgentProfile(
            agent_id=role["agent_id"],
            role_code=role["role_code"],
            role_name=role["role_name"],
            name=name,
            rank=role["rank"],
            specialty=role["specialty"],
            persona=persona,
            risk_tolerance=role["default_risk_tolerance"],
            analytical_depth=role["default_analytical_depth"],
            doctrinal_adherence=role["default_doctrinal_adherence"],
            expertise_maneuver=defaults["maneuver"],
            expertise_fires=defaults["fires"],
            expertise_logistics=defaults["logistics"],
            expertise_intel=defaults["intel"],
            expertise_comms=defaults["comms"],
            assigned_entity_uuids=assigned_uuids,
            assigned_entity_types=role["assigned_entity_types"],
        )

    # ============================================================================
    # T2.6 — Serialization & Output
    # ============================================================================

    @staticmethod
    def save_agents_json(agents: List[TacticalAgentProfile], output_path: str):
        """Save agent profiles to a JSON file."""
        data = {
            "agents": [a.to_dict() for a in agents],
            "total_agents": len(agents),
            "generation_method": "tactical_staff",
            "created_at": datetime.now().isoformat(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(agents)} agents to {output_path}")

    @staticmethod
    def load_agents_json(input_path: str) -> List[TacticalAgentProfile]:
        """Load agent profiles from a JSON file."""
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [TacticalAgentProfile.from_dict(a) for a in data.get("agents", [])]

    @staticmethod
    def _clamp(value, min_val=0.0, max_val=1.0) -> float:
        """Clamp a numeric value to [min_val, max_val]."""
        try:
            return max(min_val, min(max_val, float(value)))
        except (TypeError, ValueError):
            return 0.5
