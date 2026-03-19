"""
Ontology Generation Service
Analyzes document content and generates entity/relationship type definitions
for tactical/military mission analysis and decision support.
"""

import json
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient


ONTOLOGY_SYSTEM_PROMPT = """You are an expert knowledge graph ontology designer specialized in military and tactical domains. Your task is to analyze the given document content and mission analysis requirement, and design entity types and relationship types suitable for **tactical decision support and mission analysis**.

**IMPORTANT: You must output valid JSON data only. Do not output anything else.**

## Core Task Background

We are building a **tactical decision support system**. In this system:
- Each entity represents a real operational element in the battlespace: units, threats, assets, locations, objectives, routes, etc.
- Entities have relationships that reflect operational dependencies, threats, support, command, and geographic proximity.
- The knowledge graph will be used by AI staff officers to analyze the situation, develop courses of action (COAs), and support commander decisions.

Therefore, **entities must be concrete, operationally relevant elements that exist in the battlespace or mission context**:

**Valid entity categories**:
- Military units and formations (platoons, companies, battalions, brigades, task forces)
- Geographic locations and tactical positions (hills, grid references, airfields, urban areas)
- Mission objectives (named objectives, phase lines, checkpoints)
- Threats and enemy forces (enemy units, IED clusters, sniper positions, minefields, air defense)
- Assets and equipment (vehicles, UAVs, communications, weapons systems, ISR platforms)
- Routes and corridors of movement (MSRs, ASRs, infiltration lanes)
- Supply and logistics points (FOBs, LZs, field hospitals, ammo caches, water points)
- Terrain features of tactical significance (rivers, mountain passes, ridgelines, forests)
- Civilian entities in the area of operations (villages, population centers, key leaders, NGOs)
- Organizations (coalition forces, allied units, international organizations)

**Invalid entity categories** (DO NOT create these):
- Abstract concepts (strategy, tactics, morale, victory, doctrine)
- Emotional states (fear, confidence, motivation)
- Generic categories (friendly forces, enemy forces — be specific)
- Political ideologies or viewpoints

## Output Format

Output JSON with the following structure:

```json
{
    "entity_types": [
        {
            "name": "EntityTypeName (English, PascalCase)",
            "description": "Brief description (English, max 100 chars)",
            "attributes": [
                {
                    "name": "attribute_name (English, snake_case)",
                    "type": "text",
                    "description": "Attribute description"
                }
            ],
            "examples": ["Example entity 1", "Example entity 2"]
        }
    ],
    "edge_types": [
        {
            "name": "RELATIONSHIP_NAME (English, UPPER_SNAKE_CASE)",
            "description": "Brief description (English, max 100 chars)",
            "source_targets": [
                {"source": "SourceEntityType", "target": "TargetEntityType"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "Brief analysis of the document content and its operational significance"
}
```

## Design Guidelines (CRITICAL!)

### 1. Entity Type Design — Strict Rules

**Quantity: Exactly 10 entity types**

**Hierarchy (must include both specific and fallback types)**:

Your 10 entity types must follow this structure:

A. **Fallback types (MUST be the last 2 in the list)**:
   - `MilitaryUnit`: Fallback for any military unit, formation, or tactical grouping not covered by more specific types.
   - `Organization`: Fallback for any non-military organization (NGO, civilian agency, allied force, political entity).

B. **Specific types (8, designed based on document content)**:
   - Identify the most operationally significant entity categories from the document.
   - Example: If the document involves a ground assault, you might have: `InfantryUnit`, `ArmorUnit`, `Threat`, `Objective`, `Route`, `SupplyPoint`, `TerrainFeature`, `CivilianEntity`
   - Example: If the document involves ISR/recon, you might have: `ReconElement`, `Threat`, `Sensor`, `Location`, `Objective`, `Route`, `TerrainFeature`, `CivilianEntity`

**Why fallback types are needed**:
- Documents mention many entities that may not fit specific categories.
- Unclassified military units should fall into `MilitaryUnit`.
- NGOs, civilian government agencies, allied organizations should fall into `Organization`.

**Specific type design principles**:
- Identify the most frequently occurring or operationally critical entity types in the document.
- Each type should have clear boundaries — avoid overlapping definitions.
- Description must clearly state how this type differs from the fallback types.

### 2. Relationship Type Design

- Quantity: 8-10 relationship types
- Relationships must reflect **operational dependencies and tactical connections**
- Ensure source_targets cover the entity types you defined

### 3. Attribute Design

- 1-3 key attributes per entity type
- **RESERVED NAMES (cannot be used as attribute names)**: `name`, `uuid`, `group_id`, `created_at`, `summary`
- Recommended military attributes: `unit_designation`, `grid_reference`, `terrain_type`, `threat_type`, `assessed_strength`, `capability`, `quantity`, `availability`, `status`, `priority`, `conditions`, `route_condition`, `distance_km`, `elevation`, `trafficability`

## Entity Type Reference (for inspiration)

**Unit types (specific)**:
- InfantryUnit: Infantry formation (platoon, company, battalion)
- ArmorUnit: Armored/mechanized formation
- ArtilleryUnit: Artillery battery or battalion
- EngineerUnit: Combat engineer element
- ReconElement: Reconnaissance/scout element
- SpecialOpsUnit: Special operations team

**Unit type (fallback)**:
- MilitaryUnit: Any military unit not fitting specific types above

**Operational types**:
- Threat: Enemy force, IED, minefield, sniper position, air defense
- Objective: Named mission objective, phase line, checkpoint, key terrain
- Asset: Equipment, vehicle, UAV, ISR platform, weapons system, comms relay
- Route: Movement corridor (MSR, ASR, infiltration lane)
- SupplyPoint: FOB, LZ, field hospital, ammo cache, water point
- Location: Tactical position, grid reference, assembly area, airfield
- TerrainFeature: River, mountain pass, ridgeline, dense urban area, forest
- CivilianEntity: Village, refugee camp, key leader, NGO clinic, market

**Organization type (fallback)**:
- Organization: Any non-military organization (NGO, UN agency, civilian authority)

## Relationship Type Reference

- ASSIGNED_TO: Unit assigned to a mission or area
- THREATENS: Threat endangers a unit, location, or objective
- SUPPORTS: Unit or asset provides support to another element
- LOCATED_AT: Entity is positioned at a location
- CONNECTED_BY: Locations linked by a route
- SUPPLIES: Supply point provides logistics to a unit
- OVERLOOKS: Terrain feature has line of sight over a location
- ADJACENT_TO: Entities are geographically adjacent
- COMMANDS: Higher echelon commands a subordinate unit
- INTERDICTS: Threat or unit blocks/denies a route or area
"""


class OntologyGenerator:
    """
    Ontology Generator
    Analyzes document content to produce entity and relationship type definitions
    for tactical/military mission analysis.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate ontology definition from mission documents.

        Args:
            document_texts: List of document text contents
            simulation_requirement: Mission analysis requirement description
            additional_context: Additional context or instructions

        Returns:
            Ontology definition (entity_types, edge_types, analysis_summary)
        """
        user_message = self._build_user_message(
            document_texts,
            simulation_requirement,
            additional_context
        )

        messages = [
            {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )

        result = self._validate_and_process(result)

        return result

    MAX_TEXT_LENGTH_FOR_LLM = 50000

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Build the user message for ontology generation."""

        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)

        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(Original document: {original_length} chars, truncated to {self.MAX_TEXT_LENGTH_FOR_LLM} for ontology analysis)..."

        message = f"""## Mission Analysis Requirement

{simulation_requirement}

## Document Content

{combined_text}
"""

        if additional_context:
            message += f"""
## Additional Context

{additional_context}
"""

        message += """
Based on the above content, design entity types and relationship types suitable for tactical mission analysis and decision support.

**Mandatory rules**:
1. Output exactly 10 entity types
2. The last 2 must be fallback types: MilitaryUnit (unit fallback) and Organization (org fallback)
3. The first 8 are specific types designed from the document content
4. All entity types must be concrete, operationally relevant elements — no abstract concepts
5. Attribute names cannot use reserved words: name, uuid, group_id, created_at, summary
"""

        return message
    
    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and post-process the LLM-generated ontology."""

        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""

        for entity in result["entity_types"]:
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."

        for edge in result["edge_types"]:
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."

        # Zep API limits: max 10 custom entity types, max 10 custom edge types
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10

        # Fallback type definitions (military domain)
        military_unit_fallback = {
            "name": "MilitaryUnit",
            "description": "Any military unit or tactical grouping not fitting other specific types.",
            "attributes": [
                {"name": "unit_designation", "type": "text", "description": "Official unit designation"},
                {"name": "unit_size", "type": "text", "description": "Size category (squad, platoon, company, battalion, brigade)"},
                {"name": "status", "type": "text", "description": "Operational status (combat-ready, degraded, combat-ineffective)"}
            ],
            "examples": ["3rd Brigade Combat Team", "Alpha Company", "Task Force Iron"]
        }

        organization_fallback = {
            "name": "Organization",
            "description": "Any non-military organization (NGO, civilian agency, allied coalition).",
            "attributes": [
                {"name": "org_type", "type": "text", "description": "Type of organization (NGO, UN agency, civilian authority)"},
                {"name": "role", "type": "text", "description": "Role in the operational area"}
            ],
            "examples": ["UNHCR", "Red Cross", "District Government"]
        }

        entity_names = {e["name"] for e in result["entity_types"]}
        has_military_unit = "MilitaryUnit" in entity_names
        has_organization = "Organization" in entity_names

        fallbacks_to_add = []
        if not has_military_unit:
            fallbacks_to_add.append(military_unit_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)

        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)

            if current_count + needed_slots > MAX_ENTITY_TYPES:
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                result["entity_types"] = result["entity_types"][:-to_remove]

            result["entity_types"].extend(fallbacks_to_add)

        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]

        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]

        return result
    
    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        将本体定义转换为Python代码（类似ontology.py）
        
        Args:
            ontology: 本体定义
            
        Returns:
            Python代码字符串
        """
        code_lines = [
            '"""',
            'Custom entity type definitions',
            'Auto-generated by MiroFish for tactical mission analysis',
            '"""',
            '',
            'from typing import Optional',
            'from pydantic import BaseModel, Field',
            '',
            '',
            '# ============== 实体类型定义 ==============',
            '',
        ]
        
        # 生成实体类型
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(BaseModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: Optional[str] = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== 关系类型定义 ==============')
        code_lines.append('')
        
        # 生成关系类型
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # 转换为PascalCase类名
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(BaseModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: Optional[str] = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # 生成类型字典
        code_lines.append('# ============== 类型配置 ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # 生成边的source_targets映射
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

