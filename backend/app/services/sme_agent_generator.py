"""
SME Agent Generator
Selects the N most relevant entities from the knowledge graph and generates
rich Subject Matter Expert personas that participate as local witnesses/experts
in MDMP deliberation phases.

Reuses Graphiti enrichment from OasisProfileGenerator for 2-pass entity context.
"""

import json
import random
import time
import concurrent.futures
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from openai import OpenAI

from ..config import Config
from ..utils.graphiti_client import get_graphiti, run_async
from ..utils.logger import get_logger
from .zep_entity_reader import EntityNode, EntityReader
from .tactical_agent_generator import SMEAgentProfile

logger = get_logger('mirofish.sme_agents')


# ============================================================================
# Phase relevance by entity type
# ============================================================================

ENTITY_TYPE_PHASE_MAP: Dict[str, List[int]] = {
    "CivilianEntity": [1, 3, 5],
    "Persona": [1, 3, 5],
    "Threat": [2, 4],
    "TerrainFeature": [1, 2, 3],
    "Location": [1, 2, 3],
    "Asset": [3, 4, 7],
    "SupplyPoint": [3, 4, 7],
    "Route": [1, 2, 3],
    "Objective": [2, 3, 4],
}

# Entity types already well-covered by staff officers — lower priority for SME
STAFF_COVERED_TYPES = {"MilitaryUnit", "Objective"}

# Expertise tag mapping
ENTITY_TYPE_TAGS: Dict[str, List[str]] = {
    "CivilianEntity": ["civilian_population", "local_knowledge", "social_dynamics"],
    "Persona": ["local_knowledge", "personal_testimony", "social_dynamics"],
    "Threat": ["threat_assessment", "security_situation", "enemy_activity"],
    "TerrainFeature": ["local_terrain", "geography", "movement_corridors"],
    "Location": ["local_terrain", "area_knowledge", "infrastructure"],
    "Asset": ["resources", "equipment", "capability_assessment"],
    "SupplyPoint": ["logistics", "supply_routes", "resource_availability"],
    "Route": ["movement_corridors", "local_terrain", "accessibility"],
}


# ============================================================================
# Persona generation prompt
# ============================================================================

SME_PERSONA_SYSTEM = """You are generating a persona for a Subject Matter Expert (SME) — a local civilian witness or expert who will provide testimony during a military staff deliberation.

This person is NOT a military officer. They speak from personal, local, first-hand knowledge. They do NOT use military jargon or doctrinal analysis.

Respond with valid JSON only."""

SME_PERSONA_TEMPLATE = """Generate a detailed SME persona based on this entity from the knowledge graph:

Entity Name: {entity_name}
Entity Type: {entity_type}
Entity Summary: {entity_summary}

Rich context from knowledge graph:
{entity_context}

Mission context:
{mission_context}

Generate JSON with these fields:
1. "role_name": A descriptive title (e.g., "Local Village Elder", "NGO Field Director", "Displaced Farmer", "Tribal Leader")
2. "name": A realistic local name appropriate to the entity/region
3. "specialty": What this person knows best (1 sentence)
4. "persona": Detailed background (1500-2000 chars) including:
   - Who they are and their relationship to the entity
   - What they have personally witnessed or experienced
   - Their perspective on the situation (fears, hopes, grievances)
   - Specific local knowledge they can contribute
   - Their attitude toward military presence (cooperative, hostile, neutral, wary)
5. "expertise_tags": List of 2-4 tags from: civilian_population, local_knowledge, social_dynamics, threat_assessment, security_situation, enemy_activity, local_terrain, geography, movement_corridors, area_knowledge, infrastructure, resources, logistics, supply_routes, personal_testimony
6. "credibility": 0.0-1.0 (how reliable is this person's testimony)

IMPORTANT: This person speaks from lived experience, NOT from analysis. They tell stories, not briefings."""


class SMEAgentGenerator:
    """
    Generates SME agents from knowledge graph entities for MDMP deliberation.
    """

    def __init__(self, openai_client: Optional[OpenAI] = None):
        config = Config()
        self.graphiti = get_graphiti()
        self.openai_client = openai_client or OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.llm_model = config.LLM_MODEL_NAME
        self.sme_count = config.SME_AGENT_COUNT

    # ========================================================================
    # Entity selection & scoring
    # ========================================================================

    def score_entity(self, entity: EntityNode) -> float:
        """Score an entity's suitability for SME generation.

        Factors:
        - Connectivity (edges + related nodes)
        - Type relevance (non-military types score higher)
        - Summary richness
        """
        score = 0.0

        # Connectivity: more edges/nodes = richer context
        edge_count = len(entity.related_edges) if entity.related_edges else 0
        node_count = len(entity.related_nodes) if entity.related_nodes else 0
        score += min(edge_count * 0.5, 5.0)  # cap at 5
        score += min(node_count * 0.3, 3.0)  # cap at 3

        # Summary richness
        summary_len = len(entity.summary or "")
        score += min(summary_len / 100.0, 3.0)  # cap at 3

        # Type relevance penalty for staff-covered types
        entity_type = self._get_entity_type(entity)
        if entity_type in STAFF_COVERED_TYPES:
            score *= 0.3

        # Bonus for civilian/location types (most valuable as SMEs)
        if entity_type in ("CivilianEntity", "Persona", "Location"):
            score *= 1.5

        return round(score, 2)

    def select_top_entities(
        self,
        entities: List[EntityNode],
        count: int = 5,
    ) -> List[EntityNode]:
        """Select the top N entities by SME suitability score, ensuring type diversity."""
        scored = [(e, self.score_entity(e)) for e in entities]
        scored.sort(key=lambda x: x[1], reverse=True)

        selected = []
        types_seen: Dict[str, int] = {}
        max_per_type = max(2, count // 2)

        for entity, score in scored:
            if len(selected) >= count:
                break
            etype = self._get_entity_type(entity)
            if types_seen.get(etype, 0) >= max_per_type:
                continue
            types_seen[etype] = types_seen.get(etype, 0) + 1
            selected.append(entity)

        logger.info(f"Selected {len(selected)}/{len(entities)} entities for SME generation "
                     f"(types: {dict(types_seen)})")
        return selected

    # ========================================================================
    # Graphiti enrichment (reuses OASIS patterns)
    # ========================================================================

    def _search_graphiti_for_entity(self, entity: EntityNode, graph_id: str) -> Dict[str, Any]:
        """Search Graphiti for rich entity context (edges + nodes)."""
        from graphiti_core.search.search_config_recipes import (
            EDGE_HYBRID_SEARCH_RRF, NODE_HYBRID_SEARCH_RRF,
        )
        import copy

        results = {"facts": [], "node_summaries": [], "context": ""}

        if not graph_id:
            return results

        query = f"All information about {entity.name}: activities, events, relationships, background"

        def search_edges():
            max_retries = 3
            delay = 2.0
            for attempt in range(max_retries):
                try:
                    config = copy.deepcopy(EDGE_HYBRID_SEARCH_RRF)
                    config.limit = 20
                    return run_async(self.graphiti.search_(
                        query=query, config=config, group_ids=[graph_id],
                    ))
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Edge search failed for {entity.name}: {e}")
            return None

        def search_nodes():
            max_retries = 3
            delay = 2.0
            for attempt in range(max_retries):
                try:
                    config = copy.deepcopy(NODE_HYBRID_SEARCH_RRF)
                    config.limit = 15
                    return run_async(self.graphiti.search_(
                        query=query, config=config, group_ids=[graph_id],
                    ))
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Node search failed for {entity.name}: {e}")
            return None

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)

            facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        facts.add(edge.fact)
            results["facts"] = list(facts)

            summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity.name:
                        summaries.add(f"Related entity: {node.name}")
            results["node_summaries"] = list(summaries)

            parts = []
            if results["facts"]:
                parts.append("Facts:\n" + "\n".join(f"- {f}" for f in results["facts"][:15]))
            if results["node_summaries"]:
                parts.append("Related entities:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(parts)

            logger.info(f"Graphiti enrichment for {entity.name}: "
                         f"{len(results['facts'])} facts, {len(results['node_summaries'])} nodes")

        except Exception as e:
            logger.warning(f"Graphiti enrichment failed for {entity.name}: {e}")

        return results

    def _build_entity_context(self, entity: EntityNode, graph_id: str) -> str:
        """Build full context for an entity (edges + nodes + Graphiti search)."""
        parts = []

        # Entity attributes
        if entity.attributes:
            attrs = [f"- {k}: {v}" for k, v in entity.attributes.items() if v and str(v).strip()]
            if attrs:
                parts.append("### Entity attributes\n" + "\n".join(attrs))

        # Related edges (facts)
        existing_facts = set()
        if entity.related_edges:
            rels = []
            for edge in entity.related_edges:
                fact = edge.get("fact", "")
                if fact:
                    rels.append(f"- {fact}")
                    existing_facts.add(fact)
            if rels:
                parts.append("### Known facts and relationships\n" + "\n".join(rels))

        # Related nodes
        if entity.related_nodes:
            related = []
            for node in entity.related_nodes:
                name = node.get("name", "")
                labels = [l for l in node.get("labels", []) if l not in ("Entity", "Node")]
                summary = node.get("summary", "")
                label_str = f" ({', '.join(labels)})" if labels else ""
                if summary:
                    related.append(f"- **{name}**{label_str}: {summary}")
                else:
                    related.append(f"- **{name}**{label_str}")
            if related:
                parts.append("### Related entities\n" + "\n".join(related))

        # Graphiti search enrichment
        search = self._search_graphiti_for_entity(entity, graph_id)
        if search.get("facts"):
            new_facts = [f for f in search["facts"] if f not in existing_facts]
            if new_facts:
                parts.append("### Additional facts from search\n" + "\n".join(f"- {f}" for f in new_facts[:15]))
        if search.get("node_summaries"):
            parts.append("### Additional related nodes\n" + "\n".join(f"- {s}" for s in search["node_summaries"][:10]))

        return "\n\n".join(parts)

    # ========================================================================
    # SME persona generation
    # ========================================================================

    def _generate_sme_persona(
        self,
        entity: EntityNode,
        entity_context: str,
        mission_context: str,
        agent_id: int,
    ) -> SMEAgentProfile:
        """Generate a single SME agent profile from an entity."""
        entity_type = self._get_entity_type(entity)
        role_code = f"SME_{agent_id - 99:03d}"

        try:
            user_msg = SME_PERSONA_TEMPLATE.format(
                entity_name=entity.name,
                entity_type=entity_type,
                entity_summary=(entity.summary or "")[:500],
                entity_context=entity_context[:4000],
                mission_context=mission_context[:2000],
            )

            response = self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": SME_PERSONA_SYSTEM},
                    {"role": "user", "content": user_msg},
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

            relevant_phases = ENTITY_TYPE_PHASE_MAP.get(entity_type, [1, 3, 5])
            default_tags = ENTITY_TYPE_TAGS.get(entity_type, ["local_knowledge"])

            return SMEAgentProfile(
                agent_id=agent_id,
                role_code=role_code,
                role_name=data.get("role_name", f"Local Expert ({entity_type})"),
                name=data.get("name", entity.name),
                specialty=data.get("specialty", f"Expert on {entity.name}"),
                persona=str(data.get("persona", "")).replace("\n", " ")[:2500],
                source_entity_uuid=entity.uuid,
                source_entity_type=entity_type,
                relevant_phases=relevant_phases,
                expertise_tags=data.get("expertise_tags", default_tags)[:6],
                credibility=max(0.0, min(1.0, float(data.get("credibility", 0.7)))),
            )

        except Exception as e:
            logger.warning(f"SME persona generation failed for {entity.name}: {e}")
            return self._generate_sme_fallback(entity, entity_type, agent_id, role_code)

    def _generate_sme_fallback(
        self,
        entity: EntityNode,
        entity_type: str,
        agent_id: int,
        role_code: str,
    ) -> SMEAgentProfile:
        """Rule-based fallback for SME generation."""
        relevant_phases = ENTITY_TYPE_PHASE_MAP.get(entity_type, [1, 3, 5])
        tags = ENTITY_TYPE_TAGS.get(entity_type, ["local_knowledge"])

        persona = (
            f"A local expert with direct knowledge of {entity.name}. "
            f"Has lived in the area for many years and witnessed significant events. "
            f"Speaks from personal experience rather than analysis. "
            f"{(entity.summary or '')[:500]}"
        )

        return SMEAgentProfile(
            agent_id=agent_id,
            role_code=role_code,
            role_name=f"Local Expert ({entity_type})",
            name=entity.name,
            specialty=f"First-hand knowledge of {entity.name}",
            persona=persona,
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
            relevant_phases=relevant_phases,
            expertise_tags=tags,
            credibility=0.6,
        )

    # ========================================================================
    # Main entry point
    # ========================================================================

    def generate_sme_agents(
        self,
        graph_id: str,
        mission_context: str,
        entities: Optional[List[EntityNode]] = None,
        count: Optional[int] = None,
        progress_callback=None,
    ) -> List[SMEAgentProfile]:
        """
        Generate SME agents from the top entities in the knowledge graph.

        Args:
            graph_id: Graphiti graph ID.
            mission_context: Mission analysis text for persona generation.
            entities: Pre-loaded entities (if None, reads from graph).
            count: Number of SMEs to generate (defaults to config SME_AGENT_COUNT).
            progress_callback: Optional callback(pct, message).

        Returns:
            List of SMEAgentProfile instances.
        """
        target_count = count or self.sme_count

        if progress_callback:
            progress_callback(5, "Loading entities for SME selection...")

        if entities is None:
            reader = EntityReader()
            filtered = reader.filter_defined_entities(graph_id=graph_id)
            entities = filtered.entities if hasattr(filtered, 'entities') else filtered.get("entities", [])

        if not entities:
            logger.warning("No entities available for SME generation")
            return []

        # Select top entities
        if progress_callback:
            progress_callback(15, f"Scoring and selecting top {target_count} entities...")

        top_entities = self.select_top_entities(entities, count=target_count)

        # Generate personas
        sme_agents = []
        for i, entity in enumerate(top_entities):
            agent_id = 100 + i  # SME IDs start at 100
            pct = 20 + int((i / max(len(top_entities), 1)) * 70)

            if progress_callback:
                progress_callback(pct, f"Generating SME persona: {entity.name}")

            logger.info(f"Generating SME {i + 1}/{len(top_entities)}: {entity.name}")

            # Enrich entity context
            entity_context = self._build_entity_context(entity, graph_id)

            # Generate persona
            profile = self._generate_sme_persona(entity, entity_context, mission_context, agent_id)
            sme_agents.append(profile)

        if progress_callback:
            progress_callback(95, f"Generated {len(sme_agents)} SME agents")

        logger.info(f"Generated {len(sme_agents)} SME agents from graph entities")
        return sme_agents

    # ========================================================================
    # Utilities
    # ========================================================================

    @staticmethod
    def _get_entity_type(entity: EntityNode) -> str:
        """Extract primary custom type from entity labels."""
        generic = {"Entity", "Node"}
        for label in entity.labels:
            if label not in generic:
                return label
        return "Unknown"
