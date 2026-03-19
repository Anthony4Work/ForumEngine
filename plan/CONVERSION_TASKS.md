# MiroFish Tactical Conversion — Master Task Registry

> **Proyecto**: Transformar MiroFish de simulador de opinion publica en redes sociales a sistema de soporte a decisiones tacticas/militares
> **Estado Global**: `43 / 47 tareas completadas`
> **Ultima actualizacion**: 2026-03-18

---

## Tabla de Contenidos

- [Resumen de Arquitectura](#resumen-de-arquitectura)
- [Leyenda de Estados](#leyenda-de-estados)
- [Progreso por Fase](#progreso-por-fase)
- [FASE 1 — Ontologia Militar](#fase-1--ontologia-militar)
- [FASE 2 — Generador de Agentes Tacticos](#fase-2--generador-de-agentes-tacticos)
- [FASE 3 — Motor de Deliberacion Tactica (MDMP)](#fase-3--motor-de-deliberacion-tactica-mdmp)
- [FASE 4 — Config Generator Adaptado](#fase-4--config-generator-adaptado)
- [FASE 5 — Integracion Backend (Manager, Runner, IPC, Memory)](#fase-5--integracion-backend-manager-runner-ipc-memory)
- [FASE 6 — Report Agent Adaptado](#fase-6--report-agent-adaptado)
- [FASE 7 — API y Frontend](#fase-7--api-y-frontend)
- [FASE 8 — Testing y Validacion](#fase-8--testing-y-validacion)
- [Riesgos y Mitigaciones](#riesgos-y-mitigaciones)
- [Componentes que se Reutilizan sin Cambios](#componentes-que-se-reutilizan-sin-cambios)

---

## Resumen de Arquitectura

```
ACTUAL (Social Media Simulation)           OBJETIVO (Tactical Decision Support)
═══════════════════════════════            ═══════════════════════════════════

Documento de noticias                      Documento de mision (OPORD/FRAGO)
       │                                          │
       ▼                                          ▼
Ontologia social                           Ontologia militar
(Person, Organization,                     (MilitaryUnit, Threat, Asset,
 Student, MediaOutlet...)                   Location, Objective, Route...)
       │                                          │
       ▼                                          ▼
Grafo de conocimiento Zep      ══════>     Grafo de conocimiento Zep
(se reutiliza sin cambios)                 (se reutiliza sin cambios)
       │                                          │
       ▼                                          ▼
Perfiles sociales OASIS                    Agentes Estado Mayor tactico
(karma, followers, MBTI,                   (CDR, S2, S3, S4, RED, FSO,
 bio, posting style...)                     risk_tolerance, expertise...)
       │                                          │
       ▼                                          ▼
Simulacion OASIS                           Motor de Deliberacion MDMP
(Twitter: post/like/repost)                (7 fases: Mission Analysis →
(Reddit: post/comment/vote)                 COA Dev → Wargaming → Decision)
       │                                          │
       ▼                                          ▼
Reporte de opinion publica                 Reporte tactico (OPORD)
(tendencias, sentimiento,                  (COAs rankeados, matriz de
 influencers, narrativas...)                riesgo, recomendacion...)
       │                                          │
       ▼                                          ▼
Chat sobre el reporte          ══════>     Chat sobre decisiones tacticas
(InsightForge se reutiliza)                (InsightForge se reutiliza)
```

**Reutilizable (~40%)**: Zep GraphRAG, InsightForge/PanoramaSearch/QuickSearch, IPC, modelos Project/Task, API graph/report, frontend skeleton, utilities
**Reescritura (~60%)**: Ontologia, perfiles de agentes, motor de simulacion (OASIS → MDMP), config generator, memory updater, API simulation, frontend Steps 2-3

---

## Leyenda de Estados

| Marcador | Significado |
|:--------:|-------------|
| `[ ]` | **TODO** — Pendiente, no iniciada |
| `[~]` | **IN PROGRESS** — En curso |
| `[x]` | **DONE** — Completada y verificada |
| `[!]` | **BLOCKED** — Bloqueada por dependencia o decision pendiente |

---

## Progreso por Fase

| Fase | Nombre | Tareas | Completadas | Estado |
|:----:|--------|:------:|:-----------:|:------:|
| 1 | Ontologia Militar | 5 | 5 | `[x]` |
| 2 | Generador de Agentes Tacticos | 6 | 6 | `[x]` |
| 3 | Motor de Deliberacion MDMP | 9 | 9 | `[x]` |
| 4 | Config Generator Adaptado | 5 | 5 | `[x]` |
| 5 | Integracion Backend | 7 | 7 | `[x]` |
| 6 | Report Agent Adaptado | 4 | 4 | `[x]` |
| 7 | API y Frontend | 7 | 7 | `[x]` |
| 8 | Testing y Validacion | 4 | 0 | `[ ]` |
| **TOTAL** | | **47** | **0** | |

---

## FASE 1 — Ontologia Militar

> **Objetivo**: Reemplazar los prompts de generacion de ontologia social por prompts que extraigan entidades y relaciones militares/tacticas de documentos de mision.
> **Archivo principal**: `backend/app/services/ontology_generator.py`
> **Esfuerzo estimado**: Bajo — solo se reescriben prompts y constantes, la logica de generacion y validacion se mantiene.
> **Dependencias**: Ninguna — esta es la primera fase.

---

### T1.1 — Reescribir `ONTOLOGY_SYSTEM_PROMPT` con dominio militar

`[x]` **DONE**

**Archivo**: `backend/app/services/ontology_generator.py`
**Lineas afectadas**: Variable `ONTOLOGY_SYSTEM_PROMPT` (prompt principal del LLM)

**Que hay ahora**:
El prompt actual dice textualmente: *"你是一个专业的知识图谱本体设计专家。你的任务是分析给定的文本内容和模拟需求，设计适合社交媒体舆论模拟的实体类型和关系类型"* (Eres un experto en ontologias. Tu tarea es disenar tipos de entidad adecuados para simulacion de opinion publica en redes sociales).

Las restricciones actuales prohiben entidades abstractas (opinion, emocion, tendencia) y solo permiten entidades que "pueden hablar en redes sociales" — personas y organizaciones.

**Que debe quedar**:
Un nuevo prompt que instruya al LLM a extraer entidades del **dominio tactico/militar**:

- **Tipos de entidad permitidos** (10, respetando el limite de Zep):
  | # | Tipo | Descripcion | Atributos recomendados |
  |---|------|-------------|----------------------|
  | 1 | `MilitaryUnit` | Formacion militar (peloton, compania, batallon, brigada) | `unit_designation`, `size`, `type`, `strength`, `status` |
  | 2 | `Location` | Punto geografico tactico (grid, coordenadas, nombre) | `grid_reference`, `terrain_type`, `elevation`, `description` |
  | 3 | `Objective` | Meta de mision nombrada (asegurar, capturar, reconocer) | `objective_name`, `priority`, `conditions`, `description` |
  | 4 | `Threat` | Amenaza identificada (fuerza enemiga, IED, emboscada, mina) | `threat_type`, `assessed_strength`, `probability`, `description` |
  | 5 | `Asset` | Recurso/equipo disponible (vehiculo, dron, arma, ISR, comms) | `asset_type`, `capability`, `quantity`, `availability` |
  | 6 | `Route` | Corredor de movimiento (MSR, ASR, ruta de infiltracion) | `route_name`, `condition`, `trafficability`, `length_km` |
  | 7 | `SupplyPoint` | Nodo logistico (FOB, LZ, punto de agua, hospital de campana) | `facility_type`, `capacity`, `status`, `description` |
  | 8 | `TerrainFeature` | Terreno tactico significativo (rio, paso, cresta, bosque) | `feature_type`, `tactical_significance`, `description` |
  | 9 | `CivilianEntity` | Poblacion, lideres clave, NGOs en el Area de Operaciones | `entity_type`, `population`, `attitude`, `description` |
  | 10 | `Organization` | **Fallback** — cualquier organizacion no clasificada | `org_type`, `role`, `description` |

- **Tipos de relacion** (8-10):
  `ASSIGNED_TO`, `THREATENS`, `SUPPORTS`, `LOCATED_AT`, `CONNECTED_BY`, `SUPPLIES`, `OVERLOOKS`, `ADJACENT_TO`, `COMMANDS`, `INTERDICTS`

- **Categorias prohibidas**: Conceptos abstractos (estrategia, tactica, moral, victoria), estados emocionales, categorias politicas genericas.

**Criterio de aceptacion**:
- Subir un OPORD de ejemplo en ingles → el sistema genera exactamente 10 entity types militares y 8-10 edge types relevantes.
- Ninguna entidad generada es de tipo social (Student, Professor, MediaOutlet, etc.).
- Los fallback types son `MilitaryUnit` y `Organization` (no `Person`/`Organization`).

---

### T1.2 — Actualizar tipos de entidad de referencia y ejemplos

`[x]` **DONE**

**Archivo**: `backend/app/services/ontology_generator.py`
**Lineas afectadas**: Seccion de "参考实体类型" (tipos de referencia) dentro del prompt

**Que hay ahora**:
El prompt incluye tipos de referencia como inspiracion para el LLM: `Student`, `Professor`, `Journalist`, `Celebrity`, `Executive`, `Official`, `University`, `Company`, `GovernmentAgency`, `MediaOutlet`, `Hospital`, `School`, `NGO`.

**Que debe quedar**:
Reemplazar con tipos de referencia militares:

```
Referencia de tipos de entidad militar:
- Unidades: Infantry_Platoon, Mechanized_Company, Artillery_Battery, Engineer_Squad
- Localizaciones: Hilltop, Urban_Center, River_Crossing, Airfield, Assembly_Area
- Objetivos: Named_Objective, Phase_Line, Checkpoint, Key_Terrain
- Amenazas: Enemy_Infantry, IED_Belt, Sniper_Position, Enemy_Armor, AA_Battery
- Recursos: UAS, MRAP, Comms_Relay, Medical_Station, Ammo_Cache
- Rutas: Main_Supply_Route, Alternate_Supply_Route, Infiltration_Lane
- Terreno: River, Mountain_Pass, Dense_Urban, Open_Desert, Forested_Ridge
- Civiles: Village, Refugee_Camp, Market, District_Leader, NGO_Clinic
```

**Criterio de aceptacion**:
- LLM genera entidades contextualmente apropiadas al documento militar subido, inspiradas por los nuevos tipos de referencia.

---

### T1.3 — Actualizar restricciones de atributos reservados

`[x]` **DONE**

**Archivo**: `backend/app/services/ontology_generator.py`
**Lineas afectadas**: Seccion de atributos prohibidos y recomendados dentro del prompt

**Que hay ahora**:
Atributos recomendados: `full_name`, `org_name`, `title`, `role`, `position`, `location`, `description`.
Atributos prohibidos (reservados por Zep): `name`, `uuid`, `group_id`, `created_at`, `summary`.

**Que debe quedar**:
Mantener los atributos prohibidos (son restriccion de Zep, no del dominio). Cambiar los recomendados:

```
Atributos recomendados para entidades militares:
- unit_designation, size, strength, status, readiness
- grid_reference, terrain_type, elevation, trafficability
- threat_type, assessed_strength, probability, last_observed
- asset_type, capability, quantity, availability, range_km
- route_condition, distance_km, chokepoints
- priority, conditions, time_constraint
```

**Criterio de aceptacion**:
- Las entidades generadas usan atributos tacticos relevantes (no `full_name` o `title`).
- Ningun atributo usa nombres reservados por Zep.

---

### T1.4 — Actualizar `_validate_and_process()` — fallback types

`[x]` **DONE**

**Archivo**: `backend/app/services/ontology_generator.py`
**Funcion**: `_validate_and_process()`

**Que hay ahora**:
La validacion fuerza que los 2 ultimos entity types sean `Person` (individual fallback) y `Organization` (org fallback). Si el LLM no los incluye, el metodo los anade.

**Que debe quedar**:
Cambiar los fallback types a `MilitaryUnit` (fallback para unidades/entidades tacticas no clasificadas) y `Organization` (se mantiene como fallback generico).

Tambien actualizar la descripcion de los fallback:
- `MilitaryUnit`: "Unidad militar o agrupacion tactica que no encaja en los tipos especificos definidos"
- `Organization`: "Organizacion no militar (ONG, agencia civil, entidad politica)"

**Criterio de aceptacion**:
- Si el LLM genera menos de 10 types, el sistema anade `MilitaryUnit` y `Organization` automaticamente.
- Si el LLM ya los incluye, no se duplican.

---

### T1.5 — Actualizar `_build_user_message()` — contexto del documento

`[x]` **DONE**

**Archivo**: `backend/app/services/ontology_generator.py`
**Funcion**: `_build_user_message()`

**Que hay ahora**:
El user message incluye: el texto combinado de los documentos (max 50,000 chars), el `simulation_requirement` del usuario, y pide disenar ontologia "para simulacion de opinion publica".

**Que debe quedar**:
Cambiar la instruccion final de "disenar ontologia para opinion publica en redes sociales" a "disenar ontologia para analisis de mision y soporte a decisiones tacticas". El campo `simulation_requirement` pasa a ser `analysis_requirement` (contexto del analisis de mision que el usuario quiere).

**Criterio de aceptacion**:
- El user message no contiene ninguna referencia a redes sociales, opinion publica, o simulacion social.
- El LLM recibe instrucciones claras de extraer entidades tacticas.

---

## FASE 2 — Generador de Agentes Tacticos

> **Objetivo**: Crear un nuevo servicio que genere un Estado Mayor tactico de ~10 agentes con roles fijos (CDR, S2, S3, S4, RED...), reemplazando el generador de perfiles de redes sociales.
> **Archivo principal**: `backend/app/services/tactical_agent_generator.py` (NUEVO)
> **Reemplaza**: `backend/app/services/oasis_profile_generator.py`
> **Esfuerzo estimado**: Medio — nuevo archivo, pero reutiliza el patron de generacion con LLM y la conexion a Zep.
> **Dependencias**: Fase 1 completada (necesita ontologia militar para asignar entidades a agentes).

---

### T2.1 — Definir dataclass `TacticalAgentProfile`

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py` (NUEVO)

**Que hay ahora (en `oasis_profile_generator.py`)**:
`OasisAgentProfile` con campos de redes sociales: `user_id`, `user_name`, `bio` (200 chars), `persona` (2000 chars), `karma`, `friend_count`, `follower_count`, `statuses_count`, `age`, `gender`, `mbti`, `country`, `profession`, `interested_topics`.

**Que debe quedar**:
Nuevo dataclass completamente diferente:

```python
@dataclass
class TacticalAgentProfile:
    agent_id: int
    role_code: str               # "CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"
    role_name: str               # "Commander", "Intelligence Officer", etc.
    name: str                    # Nombre generado por LLM (ej: "COL James Mitchell")
    rank: str                    # "COL", "LTC", "MAJ", "CPT"
    specialty: str               # "Intelligence", "Operations", "Logistics", etc.
    persona: str                 # 2000 chars: background, experiencia, como evalua situaciones

    # Perfil cognitivo (0.0-1.0) — reemplaza MBTI
    risk_tolerance: float        # 0.0 = muy conservador, 1.0 = agresivo
    analytical_depth: float      # 0.0 = rapido e intuitivo, 1.0 = profundo y metódico
    doctrinal_adherence: float   # 0.0 = creativo/flexible, 1.0 = estricto con doctrina

    # Expertise por dominio (0.0-1.0) — reemplaza interested_topics
    expertise_maneuver: float    # Movimiento y maniobra
    expertise_fires: float       # Fuegos directos e indirectos
    expertise_logistics: float   # Sostenimiento y logistica
    expertise_intel: float       # Inteligencia y reconocimiento
    expertise_comms: float       # Comunicaciones y C2

    # Mapping al grafo de conocimiento
    assigned_entity_uuids: List[str]   # Entidades del grafo bajo responsabilidad de este agente
    assigned_entity_types: List[str]   # Tipos de entidad que monitorea
    source_entity_type: Optional[str]
    created_at: str
```

**Cambio conceptual clave**: En el sistema social, *cada entidad del grafo se convierte en un agente* (1 persona = 1 agente). En el sistema tactico, *los agentes son un Estado Mayor fijo de 10 roles*. Las entidades del grafo son los **datos sobre los que razonan**, no los agentes mismos.

**Criterio de aceptacion**:
- Dataclass definido con todos los campos listados.
- Incluye metodo `to_dict()` y `from_dict()` para serializacion JSON.
- Ningun campo social (karma, followers, MBTI, gender, bio de redes sociales).

---

### T2.2 — Definir tabla de roles predefinidos del Estado Mayor

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py`

**Descripcion**:
Crear una constante `STAFF_ROLES` como lista de diccionarios con la plantilla fija de roles. Estos roles NO se generan por LLM — son predefinidos por doctrina militar:

| `role_code` | `role_name` | `rank` | `specialty` | Entidades asignadas (por tipo) | Funcion en deliberacion |
|:-----------:|-------------|:------:|-------------|-------------------------------|------------------------|
| `CDR` | Commander | COL | Command | **Todas** (vision global) | Decision final, pondera todos los inputs, emite commander's intent |
| `XO` | Executive Officer | LTC | Coordination | **Todas** (coordinacion) | Coordina staff, challenge de supuestos, gestiona tiempo |
| `S2` | Intelligence Officer | MAJ | Intelligence | `Threat`, `TerrainFeature`, `CivilianEntity` | Analisis de amenazas, preparacion de inteligencia del campo de batalla (IPB), COAs enemigos |
| `S3` | Operations Officer | MAJ | Operations | `MilitaryUnit`, `Objective`, `Route` | Planifica maniobra, sincroniza acciones, desarrolla COAs amigos |
| `S4` | Logistics Officer | MAJ | Logistics | `SupplyPoint`, `Asset` (logisticos) | Evalua sostenimiento, rutas de suministro, capacidad medica |
| `S6` | Communications Officer | CPT | Communications | `Asset` (comms) | Evalua redes C2, redundancia de comunicaciones, vulnerabilidades de senal |
| `FSO` | Fire Support Officer | MAJ | Fires | `Asset` (armas/fuegos), `Location` | Planifica fuegos de apoyo, evalua dano colateral, coordina CAS |
| `RED` | Red Team (Adversario) | LTC | Adversary | `Threat`, `MilitaryUnit` (perspectiva enemiga) | **Piensa como el enemigo**: challenge COAs propios, propone COAs enemigos, identifica vulnerabilidades |
| `CIMIC` | Civil-Military Coord | CPT | Civil Affairs | `CivilianEntity`, `Location` | Impacto en poblacion civil, restricciones ROE, coordinacion con NGOs |
| `ENGR` | Engineer Officer | CPT | Engineering | `TerrainFeature`, `Route`, `Threat` (IEDs) | Movilidad/contra-movilidad, desminado, modificacion de terreno, construccion |

**Criterio de aceptacion**:
- Constante `STAFF_ROLES` con exactamente 10 roles.
- Cada rol tiene mapping de `assigned_entity_types` → lista de tipos de entidad del grafo que monitorea.
- Los roles CDR y XO tienen acceso a todas las entidades.

---

### T2.3 — Implementar asignacion automatica entidad→agente

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py`
**Funcion**: `assign_entities_to_agents(entities: List[EntityNode], roles: List[dict]) -> Dict[str, List[str]]`

**Que hay ahora (en `oasis_profile_generator.py`)**:
No existe — en el sistema social, cada entidad ES un agente (mapeo 1:1).

**Que debe quedar**:
Algoritmo de asignacion entidad→agente basado en el tipo de entidad:

```
1. Para cada entidad filtrada del grafo (via ZepEntityReader):
   a. Obtener su label/tipo (ej: "Threat", "MilitaryUnit")
   b. Buscar en STAFF_ROLES que roles tienen ese tipo en assigned_entity_types
   c. Asignar el UUID de la entidad a todos los roles que lo monitorean

2. CDR y XO reciben TODOS los UUIDs (vision completa)

3. Si una entidad no encaja en ningun tipo → asignar a CDR como fallback
```

**Ejemplo concreto**:
```
Entidad "IED Cluster Alpha" (tipo: Threat)
  → Asignada a: S2 (intel), RED (adversario), ENGR (desminado)

Entidad "3rd Platoon" (tipo: MilitaryUnit)
  → Asignada a: S3 (operaciones), RED (perspectiva enemiga)

Entidad "FOB Falcon" (tipo: SupplyPoint)
  → Asignada a: S4 (logistica)

Todas las entidades → CDR, XO (siempre)
```

**Criterio de aceptacion**:
- Cada entidad del grafo esta asignada al menos a un agente.
- CDR y XO tienen la lista completa de todas las entidades.
- No hay entidades huerfanas (sin agente asignado).

---

### T2.4 — Implementar generacion de persona por LLM

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py`
**Funcion**: `generate_agent_persona(role: dict, entities: List[EntityNode], mission_context: str) -> TacticalAgentProfile`

**Que hay ahora (en `oasis_profile_generator.py`)**:
LLM genera `bio` (200 chars) y `persona` (2000 chars) con datos de redes sociales: estilo de posteo, frecuencia, que contenido le gusta, MBTI, edad, genero.

**Que debe quedar**:
LLM genera `persona` (2000 chars) con datos tacticos:

```
Prompt al LLM:
"Genera una persona detallada para un oficial militar con el siguiente rol:

Rol: {role_name} ({role_code})
Rango: {rank}
Especialidad: {specialty}
Contexto de mision: {mission_context}
Entidades bajo su responsabilidad: {entity_summaries}

La persona debe incluir:
1. Background profesional (20+ anos de carrera, despliegues previos)
2. Estilo de analisis (como evalua situaciones, que prioriza)
3. Sesgos conocidos (ej: S4 tiende a ser conservador con recursos)
4. Relacion con otros roles del staff (ej: S2 y S3 suelen tener tension creativa)
5. Experiencia relevante al tipo de mision actual

Tambien genera perfil cognitivo numerico:
- risk_tolerance: 0.0-1.0
- analytical_depth: 0.0-1.0
- doctrinal_adherence: 0.0-1.0
- expertise_maneuver/fires/logistics/intel/comms: 0.0-1.0

El CDR debe tener risk_tolerance moderada (0.4-0.6).
El RED Team debe tener risk_tolerance alta (0.7-0.9) y doctrinal_adherence baja (0.2-0.4).
El S4 debe tener risk_tolerance baja (0.1-0.3) y expertise_logistics alta (0.8-1.0).

Responde en JSON."
```

**Criterio de aceptacion**:
- LLM genera persona coherente con el rol militar.
- Perfil cognitivo dentro de los rangos esperados por rol.
- Fallback rule-based si LLM falla (valores predeterminados por rol).

---

### T2.5 — Implementar fallback rule-based para perfiles

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py`
**Funcion**: `_generate_rule_based_profile(role: dict) -> TacticalAgentProfile`

**Que hay ahora (en `oasis_profile_generator.py`)**:
Fallback genera: edad random, genero random, 3 topics genericos, MBTI random. Es para cuando el LLM falla.

**Que debe quedar**:
Perfiles predeterminados por rol con valores doctrinales razonables:

| Rol | risk_tolerance | analytical_depth | doctrinal_adherence | Expertise dominante |
|-----|:--------------:|:----------------:|:-------------------:|---------------------|
| CDR | 0.5 | 0.7 | 0.6 | Balanceado (0.6 en todo) |
| XO | 0.4 | 0.8 | 0.7 | Balanceado (0.6 en todo) |
| S2 | 0.3 | 0.9 | 0.5 | intel=0.95, maneuver=0.4 |
| S3 | 0.6 | 0.7 | 0.6 | maneuver=0.9, fires=0.7 |
| S4 | 0.2 | 0.8 | 0.8 | logistics=0.95, comms=0.5 |
| S6 | 0.3 | 0.7 | 0.7 | comms=0.95, intel=0.5 |
| FSO | 0.5 | 0.6 | 0.7 | fires=0.95, maneuver=0.6 |
| RED | 0.8 | 0.9 | 0.3 | intel=0.8, maneuver=0.8 |
| CIMIC | 0.3 | 0.7 | 0.5 | intel=0.6, logistics=0.5 |
| ENGR | 0.4 | 0.8 | 0.7 | maneuver=0.7, logistics=0.6 |

**Criterio de aceptacion**:
- Si el LLM falla, el sistema genera los 10 agentes con valores por defecto.
- Los valores son doctrinalmente coherentes (RED tiene alto riesgo, S4 conservador).

---

### T2.6 — Implementar serializacion a JSON y orquestacion

`[x]` **DONE**

**Archivo**: `backend/app/services/tactical_agent_generator.py`
**Funcion**: `generate_all_agents(graph_id, mission_context) -> List[TacticalAgentProfile]`

**Que hay ahora (en `oasis_profile_generator.py`)**:
Genera perfiles en paralelo (5 workers), escribe a CSV (Twitter) o JSON (Reddit), soporta escritura incremental en tiempo real.

**Que debe quedar**:
- Generar los 10 agentes secuencialmente o en paralelo (menos urgente, son solo 10).
- Escribir a un unico archivo `agents.json` con formato:

```json
{
  "agents": [
    {
      "agent_id": 0,
      "role_code": "CDR",
      "role_name": "Commander",
      "name": "COL James Mitchell",
      "rank": "COL",
      "persona": "...",
      "risk_tolerance": 0.5,
      "assigned_entity_uuids": ["uuid1", "uuid2", ...],
      ...
    },
    ...
  ],
  "total_agents": 10,
  "generation_method": "llm|rule_based|mixed",
  "created_at": "ISO-8601"
}
```

- Eliminar formatos CSV y la distincion Twitter/Reddit.
- Mantener escritura incremental para que el frontend muestre progreso.

**Criterio de aceptacion**:
- `agents.json` contiene exactamente 10 agentes con roles unicos.
- El archivo es parseable y contiene todos los campos del dataclass.
- Endpoint `/api/simulation/{sim_id}/profiles` retorna los agentes correctamente.

---

## FASE 3 — Motor de Deliberacion Tactica (MDMP)

> **Objetivo**: Crear un motor completamente nuevo que reemplace OASIS. En vez de simular redes sociales, ejecuta una deliberacion estructurada en 7 fases siguiendo el Military Decision-Making Process (MDMP).
> **Archivo principal**: `backend/scripts/run_tactical_deliberation.py` (NUEVO)
> **Elimina**: `backend/scripts/run_twitter_simulation.py`, `backend/scripts/run_reddit_simulation.py`, `backend/scripts/run_parallel_simulation.py`
> **Esfuerzo estimado**: ALTO — es el nucleo del sistema, requiere disenar el loop de deliberacion, los prompts por fase, y la logica de convergencia.
> **Dependencias**: Fase 1 (ontologia) y Fase 2 (agentes) completadas.

---

### T3.1 — Definir `TacticalActionType` enum

`[x]` **DONE**

**Archivo**: `backend/app/config.py` (modificar) + `backend/scripts/run_tactical_deliberation.py` (nuevo)

**Que hay ahora**:
`OASIS_TWITTER_ACTIONS = ['CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST']`
`OASIS_REDDIT_ACTIONS = ['LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT', ...]`

**Que debe quedar**:
Eliminar las listas de acciones sociales. Definir nuevo enum:

```python
class TacticalActionType(str, Enum):
    # === Analisis (Fases 1-2) ===
    ANALYZE_TERRAIN = "analyze_terrain"         # Evaluar terreno y su impacto tactico
    ASSESS_THREAT = "assess_threat"             # Evaluar capacidades y posiciones enemigas
    ASSESS_LOGISTICS = "assess_logistics"       # Evaluar cadena de suministro y sostenimiento
    ASSESS_COMMS = "assess_comms"               # Evaluar redes C2 y vulnerabilidades
    IDENTIFY_KEY_TERRAIN = "identify_key_terrain" # Senalar terreno critico

    # === Generacion de COA (Fase 3) ===
    PROPOSE_COA = "propose_coa"                 # Proponer un curso de accion completo
    REFINE_COA = "refine_coa"                   # Modificar un COA existente

    # === Evaluacion (Fases 4-5) ===
    EVALUATE_RISK = "evaluate_risk"             # Evaluar riesgo de un COA
    CHALLENGE_ASSUMPTION = "challenge_assumption" # Cuestionar un supuesto
    WARGAME_MOVE = "wargame_move"               # Simular un movimiento amigo en wargame
    WARGAME_COUNTER = "wargame_counter"         # Simular respuesta enemiga en wargame
    SCORE_COA = "score_coa"                     # Puntuar COA contra criterios

    # === Decision (Fase 6) ===
    DECIDE_COA = "decide_coa"                   # Seleccionar COA (solo CDR)

    # === Informacion ===
    REQUEST_INTEL = "request_intel"             # Consultar al grafo de conocimiento
    PROVIDE_INTEL = "provide_intel"             # Responder consulta de otro agente
    IDENTIFY_GAP = "identify_gap"               # Identificar laguna de inteligencia

    # === Coordinacion ===
    CONCUR = "concur"                           # Estar de acuerdo con propuesta
    DISSENT = "dissent"                         # Disentir con justificacion
    RECOMMEND = "recommend"                     # Hacer recomendacion al CDR
    TASK_ORGANIZE = "task_organize"             # Proponer organizacion de fuerzas
```

**Criterio de aceptacion**:
- Enum definido y accesible desde el motor de deliberacion.
- Cada fase tiene un subconjunto de acciones validas (no todas estan disponibles en todas las fases).
- Las acciones sociales (`CREATE_POST`, `LIKE_POST`, etc.) estan eliminadas de `config.py`.

---

### T3.2 — Definir configuracion de las 7 fases MDMP

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Constante**: `MDMP_PHASES`

**Descripcion**:
Definir la estructura de las 7 fases de deliberacion con sus parametros:

```python
MDMP_PHASES = [
    {
        "phase_id": 1,
        "phase_name": "Mission Analysis",
        "description": "Reformular la mision, identificar tareas especificas, restricciones, y capacidades disponibles",
        "max_rounds": 3,
        "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"],
        "primary_role": "XO",
        "valid_actions": ["ANALYZE_TERRAIN", "ASSESS_THREAT", "ASSESS_LOGISTICS", "ASSESS_COMMS",
                          "IDENTIFY_KEY_TERRAIN", "REQUEST_INTEL", "IDENTIFY_GAP", "CONCUR", "DISSENT"],
        "completion_criteria": "Mission restated, specified/implied tasks identified, constraints listed",
        "output_artifact": "mission_analysis_summary"
    },
    {
        "phase_id": 2,
        "phase_name": "Intelligence Preparation of the Battlefield (IPB)",
        "description": "Evaluacion detallada de amenazas, terreno, clima, y posibles COAs enemigos",
        "max_rounds": 3,
        "active_roles": ["S2", "CDR", "S3", "RED", "ENGR"],
        "primary_role": "S2",
        "valid_actions": ["ASSESS_THREAT", "ANALYZE_TERRAIN", "IDENTIFY_KEY_TERRAIN",
                          "REQUEST_INTEL", "PROVIDE_INTEL", "IDENTIFY_GAP", "WARGAME_COUNTER"],
        "completion_criteria": "Threat assessment complete, enemy COAs developed, terrain analysis done",
        "output_artifact": "ipb_summary"
    },
    {
        "phase_id": 3,
        "phase_name": "COA Development",
        "description": "Generar 2-4 cursos de accion amigos distintos y viables",
        "max_rounds": 5,
        "active_roles": ["S3", "CDR", "XO", "S2", "S4", "FSO", "ENGR", "CIMIC"],
        "primary_role": "S3",
        "valid_actions": ["PROPOSE_COA", "REFINE_COA", "ASSESS_LOGISTICS", "EVALUATE_RISK",
                          "REQUEST_INTEL", "DISSENT", "RECOMMEND", "TASK_ORGANIZE"],
        "completion_criteria": "2-4 distinct COAs developed, each with scheme of maneuver",
        "output_artifact": "coa_proposals"
    },
    {
        "phase_id": 4,
        "phase_name": "COA Analysis (Wargaming)",
        "description": "Wargame cada COA contra COAs enemigos identificados en IPB",
        "max_rounds": 5,
        "active_roles": ["RED", "S3", "S2", "FSO", "S4", "ENGR", "S6"],
        "primary_role": "RED",
        "valid_actions": ["WARGAME_MOVE", "WARGAME_COUNTER", "EVALUATE_RISK",
                          "CHALLENGE_ASSUMPTION", "REQUEST_INTEL", "IDENTIFY_GAP"],
        "completion_criteria": "Each COA wargamed, decision points identified, risks catalogued",
        "output_artifact": "wargame_results"
    },
    {
        "phase_id": 5,
        "phase_name": "COA Comparison",
        "description": "Puntuar cada COA contra criterios de evaluacion ponderados",
        "max_rounds": 3,
        "active_roles": ["CDR", "XO", "S2", "S3", "S4", "S6", "FSO", "RED", "CIMIC", "ENGR"],
        "primary_role": "XO",
        "valid_actions": ["SCORE_COA", "EVALUATE_RISK", "CONCUR", "DISSENT", "RECOMMEND"],
        "completion_criteria": "All COAs scored, comparison matrix complete",
        "output_artifact": "coa_comparison_matrix"
    },
    {
        "phase_id": 6,
        "phase_name": "COA Decision",
        "description": "El Commander selecciona un COA y emite guia de planeamiento",
        "max_rounds": 2,
        "active_roles": ["CDR", "XO"],
        "primary_role": "CDR",
        "valid_actions": ["DECIDE_COA", "RECOMMEND"],
        "completion_criteria": "COA selected, commander's guidance issued",
        "output_artifact": "coa_decision"
    },
    {
        "phase_id": 7,
        "phase_name": "Orders Production",
        "description": "Generar borrador de OPORD basado en el COA seleccionado",
        "max_rounds": 2,
        "active_roles": ["S3", "S2", "S4", "S6", "FSO", "CIMIC", "ENGR"],
        "primary_role": "S3",
        "valid_actions": ["TASK_ORGANIZE", "RECOMMEND", "CONCUR", "DISSENT",
                          "ASSESS_LOGISTICS", "ASSESS_COMMS"],
        "completion_criteria": "Draft OPORD produced with all paragraphs",
        "output_artifact": "draft_opord"
    }
]
```

**Criterio de aceptacion**:
- 7 fases definidas con todos los campos.
- Cada fase tiene un subset coherente de `valid_actions`.
- Cada fase tiene un `primary_role` (quien lidera) y `active_roles` (quienes participan).

---

### T3.3 — Implementar el loop principal de deliberacion

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Clase**: `TacticalDeliberationEngine`
**Metodo principal**: `async run_deliberation() -> DeliberationResult`

**Que hay ahora (en `run_twitter_simulation.py`)**:
```python
for round_num in range(total_rounds):
    active_agents = self._get_active_agents_for_round(env, simulated_hour, round_num)
    actions = {agent: LLMAction() for _, agent in active_agents}
    await env.step(actions)  # OASIS decide que hace cada agente
```

**Que debe quedar**:
```python
async def run_deliberation(self):
    deliberation_log = []
    phase_summaries = {}  # Resumen comprimido de cada fase completada

    for phase in MDMP_PHASES:
        phase_log = []

        for round_num in range(phase["max_rounds"]):
            # Seleccionar agentes activos para esta ronda
            active_agents = self._get_phase_agents(phase)

            for agent in active_agents:
                # Construir contexto para el agente
                context = self._build_agent_context(
                    agent=agent,
                    phase=phase,
                    round_num=round_num,
                    phase_log=phase_log,
                    phase_summaries=phase_summaries,
                    graph_entities=agent.assigned_entity_uuids
                )

                # LLM genera accion estructurada
                action = await self._agent_act(agent, context, phase["valid_actions"])

                # Si la accion es REQUEST_INTEL, consultar el grafo
                if action.action_type == "request_intel":
                    intel_result = await self._query_graph(action.content)
                    action.intel_response = intel_result

                # Loguear y acumular
                phase_log.append(action)
                deliberation_log.append(action)
                self._log_action(action)  # Escribir a actions.jsonl

            # Evaluar si la fase esta completa
            if await self._check_phase_completion(phase, phase_log):
                break

        # Comprimir fase en resumen para no exceder ventana de contexto
        phase_summaries[phase["phase_id"]] = await self._summarize_phase(phase, phase_log)

        # Actualizar grafo con resultados de la fase
        await self._update_graph_memory(phase, phase_log)

    return DeliberationResult(phases=phase_summaries, full_log=deliberation_log)
```

**Diferencia fundamental con OASIS**: No hay `env.step()`. No hay plataforma simulada. Los agentes comparten un **registro de deliberacion** — un documento creciente de analisis, propuestas y evaluaciones. Cada agente ve el historial completo de la fase actual + resumenes de fases anteriores.

**Criterio de aceptacion**:
- El motor recorre las 7 fases secuencialmente.
- Cada fase ejecuta multiples rondas hasta `max_rounds` o convergencia.
- Las acciones se loguean a `deliberation/actions.jsonl`.
- El historial acumulado se comprime entre fases.
- Importacion de OASIS/camel-ai completamente eliminada.

---

### T3.4 — Implementar `_build_agent_context()` — prompt por turno

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `_build_agent_context(agent, phase, round_num, phase_log, phase_summaries, graph_entities)`

**Descripcion**:
Construir el prompt completo que recibe cada agente en cada turno. Este es el **corazon de la calidad del sistema** — la calidad de las deliberaciones depende directamente de la calidad de este prompt.

**Estructura del prompt**:

```
=== SYSTEM ===
Eres {agent.rank} {agent.name}, {agent.role_name} en un Estado Mayor militar.

{agent.persona}

Tu perfil cognitivo:
- Tolerancia al riesgo: {agent.risk_tolerance} (0=conservador, 1=agresivo)
- Profundidad analitica: {agent.analytical_depth} (0=rapido, 1=meticuloso)
- Adherencia doctrinal: {agent.doctrinal_adherence} (0=creativo, 1=estricto)

Tu expertise: maniobra={}, fuegos={}, logistica={}, inteligencia={}, comunicaciones={}

=== USER ===

## FASE ACTUAL: {phase.phase_name}
{phase.description}
Tu rol en esta fase: {role_specific_instructions_for_phase}

## RESUMEN DE MISION (del grafo de conocimiento)
{mission_summary}

## ENTIDADES BAJO TU RESPONSABILIDAD
{for entity in agent.assigned_entities:}
  - [{entity.type}] {entity.name}: {entity.summary}
    Relaciones: {entity.related_edges}
{endfor}

## RESUMENES DE FASES ANTERIORES
{for phase_id, summary in phase_summaries.items():}
  ### Fase {phase_id}: {summary.phase_name}
  {summary.compressed_text}  (max 500 tokens por fase)
{endfor}

## DELIBERACION DE ESTA FASE (Ronda {round_num})
{for action in phase_log:}
  [{action.agent_role}] {action.agent_name} ({action.action_type}):
  {action.content}
  Confianza: {action.confidence} | Riesgo: {action.risk_assessment}
  ---
{endfor}

## INSTRUCCIONES
Elige UNA accion de las disponibles: {phase.valid_actions}

Responde UNICAMENTE en JSON:
{
    "action_type": "accion elegida",
    "content": "tu analisis, propuesta o evaluacion detallada",
    "references": ["uuid_entidad_1", ...],  // entidades del grafo que respaldan tu analisis
    "confidence": 0.0-1.0,
    "risk_assessment": "low|medium|high|critical",
    "addressed_to": "ALL|CDR|S2|..."  // a quien va dirigido
}
```

**Gestion de ventana de contexto**:
- Resumenes de fases anteriores: max 500 tokens por fase.
- Historial de fase actual: completo (max ~20 entradas por fase).
- Entidades del agente: max 300 chars por entidad, max 20 entidades.
- Si el prompt total excede 12,000 tokens: truncar entidades menos relevantes.

**Criterio de aceptacion**:
- El prompt incluye toda la informacion necesaria para que el agente tome una decision informada.
- La informacion del grafo esta integrada (no solo texto, sino entidades con relaciones).
- El historial de deliberacion da contexto de lo que ya se discutio.
- El prompt no excede la ventana de contexto del LLM utilizado.

---

### T3.5 — Implementar `_agent_act()` — llamada LLM + parseo

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `async _agent_act(agent, context, valid_actions) -> TacticalAction`

**Descripcion**:
Llamar al LLM con el contexto construido y parsear la respuesta JSON. Incluir logica de retry y validacion.

```python
async def _agent_act(self, agent, context, valid_actions):
    response = await self.llm_client.chat_completion(
        system=context["system"],
        user=context["user"],
        temperature=0.7,
        max_tokens=2000
    )

    # Parsear JSON (reutilizar json_fixer de utils si es necesario)
    parsed = self._parse_action_json(response)

    # Validar action_type
    if parsed["action_type"] not in valid_actions:
        parsed["action_type"] = self._nearest_valid_action(parsed["action_type"], valid_actions)

    # Validar confidence y risk
    parsed["confidence"] = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
    parsed["risk_assessment"] = parsed.get("risk_assessment", "medium")
    if parsed["risk_assessment"] not in ["low", "medium", "high", "critical"]:
        parsed["risk_assessment"] = "medium"

    return TacticalAction(
        phase=self.current_phase,
        round=self.current_round,
        agent_id=agent.agent_id,
        agent_role=agent.role_code,
        agent_name=agent.name,
        **parsed
    )
```

**Criterio de aceptacion**:
- LLM retorna JSON valido con los campos requeridos.
- Si el JSON es invalido, el sistema intenta repararlo (reutilizar `json_fixer` existente).
- Si el `action_type` no es valido para la fase, se corrige al mas cercano.
- Retry con backoff si la llamada LLM falla (max 3 intentos).

---

### T3.6 — Implementar `_query_graph()` — consulta al grafo via InsightForge

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `async _query_graph(query: str) -> str`

**Descripcion**:
Cuando un agente ejecuta `REQUEST_INTEL`, el sistema consulta el grafo de conocimiento via las herramientas existentes de Zep (`InsightForge`, `QuickSearch`).

```python
async def _query_graph(self, query: str) -> str:
    # Reutilizar InsightForge de zep_tools.py
    result = await self.zep_tools.insight_forge(
        graph_id=self.graph_id,
        query=query,
        simulation_requirement=self.mission_context,
        max_sub_queries=3
    )

    # Formatear para el agente
    formatted = f"== Resultados de inteligencia para: {query} ==\n"
    for fact in result.semantic_facts[:10]:
        formatted += f"- {fact}\n"
    for entity in result.entity_insights[:5]:
        formatted += f"- [{entity.type}] {entity.name}: {entity.summary}\n"

    return formatted
```

**Criterio de aceptacion**:
- El agente puede consultar el grafo durante la deliberacion.
- Los resultados se formatean e inyectan en el historial de deliberacion.
- Otros agentes pueden ver la consulta y su resultado en rondas posteriores.
- Se reutiliza InsightForge existente (no reimplementar busqueda).

---

### T3.7 — Implementar `_check_phase_completion()` — criterio de convergencia

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `async _check_phase_completion(phase, phase_log) -> bool`

**Descripcion**:
Evaluar si una fase ha alcanzado sus criterios de completitud. Dos mecanismos:

1. **Hard limit**: Si se alcanza `max_rounds`, la fase termina siempre.
2. **LLM-based**: Un LLM "moderador" evalua si los `completion_criteria` de la fase se han cumplido.

```python
async def _check_phase_completion(self, phase, phase_log):
    if len(phase_log) >= phase["max_rounds"] * len(phase["active_roles"]):
        return True  # Hard limit

    # LLM moderador evalua completitud
    summary = "\n".join([f"[{a.agent_role}] {a.action_type}: {a.content[:200]}" for a in phase_log])

    prompt = f"""Evalua si la fase '{phase['phase_name']}' ha cumplido sus criterios de completitud.

Criterios: {phase['completion_criteria']}

Deliberacion hasta ahora:
{summary}

Responde JSON: {{"complete": true/false, "reason": "explicacion breve"}}"""

    result = await self.llm_client.chat_completion(system="Eres un moderador de procesos de Estado Mayor.", user=prompt)
    return json.loads(result).get("complete", False)
```

**Criterio de aceptacion**:
- La fase termina cuando se alcanza el hard limit O cuando el moderador LLM dice que esta completa.
- El moderador no termina fases prematuramente (bias hacia continuar si hay duda).
- El log registra por que se termino cada fase.

---

### T3.8 — Implementar `_summarize_phase()` — compresion entre fases

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `async _summarize_phase(phase, phase_log) -> PhaseSummary`

**Descripcion**:
Al terminar cada fase, comprimir todos los resultados en un resumen estructurado de ~500 tokens. Esto es critico para que el historial acumulado no exceda la ventana de contexto del LLM.

```python
async def _summarize_phase(self, phase, phase_log):
    full_text = "\n".join([f"[{a.agent_role}] {a.action_type}: {a.content}" for a in phase_log])

    prompt = f"""Resume los resultados de la fase '{phase['phase_name']}' en max 500 palabras.

Incluye:
- Decisiones clave tomadas
- Puntos de consenso
- Puntos de desacuerdo
- Artefactos producidos (COAs, evaluaciones, etc.)
- Lagunas de inteligencia identificadas

Deliberacion completa:
{full_text}"""

    summary = await self.llm_client.chat_completion(
        system="Eres un oficial de Estado Mayor que resume deliberaciones.",
        user=prompt
    )

    return PhaseSummary(
        phase_id=phase["phase_id"],
        phase_name=phase["phase_name"],
        compressed_text=summary,
        action_count=len(phase_log),
        key_decisions=[a for a in phase_log if a.action_type in ["DECIDE_COA", "PROPOSE_COA", "SCORE_COA"]]
    )
```

**Criterio de aceptacion**:
- Cada resumen es de max 500 tokens.
- El resumen captura decisiones clave sin perder informacion critica.
- Los resumenes se pasan a fases posteriores como contexto comprimido.

---

### T3.9 — Implementar COA Comparison Matrix — fase 5

`[x]` **DONE**

**Archivo**: `backend/scripts/run_tactical_deliberation.py`
**Metodo**: `_build_comparison_matrix(coas, scores) -> Dict`

**Descripcion**:
En la Fase 5 (COA Comparison), cada agente puntua cada COA contra criterios de evaluacion. El sistema agrega las puntuaciones en una matriz:

```
Criterios de evaluacion (pesos configurables):
- Probabilidad de exito de la mision: 0.30
- Proteccion de la fuerza (minimizar bajas): 0.25
- Eficiencia en tiempo: 0.15
- Sostenibilidad logistica: 0.15
- Flexibilidad (capacidad de adaptacion): 0.15

Cada agente puntua cada COA de 1-10 en cada criterio.
El peso del voto de cada agente se ajusta por su expertise relevante.
```

Ejemplo de output:

```json
{
    "criteria": [
        {"name": "Mission Success", "weight": 0.30},
        {"name": "Force Protection", "weight": 0.25},
        {"name": "Time Efficiency", "weight": 0.15},
        {"name": "Sustainability", "weight": 0.15},
        {"name": "Flexibility", "weight": 0.15}
    ],
    "coas": [
        {
            "coa_id": 1,
            "name": "Northern Approach",
            "scores": {
                "Mission Success": {"raw": 7.8, "weighted": 2.34},
                "Force Protection": {"raw": 5.2, "weighted": 1.30},
                ...
            },
            "total_weighted_score": 6.89,
            "dissenting_views": ["S4: Logistics risk too high for northern route"]
        },
        ...
    ],
    "ranking": [2, 1, 3],
    "recommended_coa": 2
}
```

**Criterio de aceptacion**:
- Matriz generada con puntuaciones numericas, no solo texto.
- Cada COA tiene un score total ponderado.
- Las vistas disidentes se capturan (no se promedian).
- El ranking es coherente con los scores.

---

## FASE 4 — Config Generator Adaptado

> **Objetivo**: Reemplazar las dataclasses y prompts de configuracion social (horarios chinos, karma, echo chambers) por configuracion de deliberacion militar (fases, criterios, parametros de mision).
> **Archivo principal**: `backend/app/services/simulation_config_generator.py`
> **Esfuerzo estimado**: Medio — reescribir dataclasses y prompts, mantener la logica de generacion LLM + fallback.
> **Dependencias**: Fase 1 completada (ontologia militar necesaria para extraer mision del documento).

---

### T4.1 — Eliminar dataclasses sociales, crear dataclasses tacticas

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_config_generator.py`

**Eliminar completamente**:
- `AgentActivityConfig` (activity_level, posts_per_hour, karma, followers, sentiment_bias, echo_chamber...)
- `TimeSimulationConfig` (peak_hours, off_peak_hours, CHINA_TIMEZONE_CONFIG, activity_multipliers...)
- `EventConfig` (initial_posts, poster_type, hot_topics, narrative_direction...)
- `PlatformConfig` (recency_weight, popularity_weight, viral_threshold, echo_chamber_strength...)

**Crear**:
- `MissionConfig`: mission_type, mission_statement, commander_intent, constraints, key_terrain, PIRs
- `DeliberationPhaseConfig`: phase_id, phase_name, max_rounds, active_roles, completion_criteria
- `TacticalAgentConfig`: agent_id, role_code, assigned_entity_uuids, decision_weight
- `DeliberationParameters`: contenedor principal con mission + phases + agents + parametros globales

(Ver dataclasses detallados en la seccion Fase 4 del plan arquitectonico.)

**Criterio de aceptacion**:
- Ninguna referencia a redes sociales, horarios, karma, followers, echo chambers.
- Todas las dataclasses tienen metodos `to_dict()` y `from_dict()`.
- `DeliberationParameters` contiene toda la informacion necesaria para ejecutar `run_tactical_deliberation.py`.

---

### T4.2 — Reescribir prompt de extraccion de MissionConfig

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_config_generator.py`

**Que hay ahora**:
LLM analiza el documento y el `simulation_requirement` para generar: `total_simulation_hours`, `minutes_per_round`, `agents_per_hour`, `peak_hours`, `off_peak_hours` (todo basado en patrones de actividad en redes sociales chinas).

**Que debe quedar**:
LLM analiza el documento de mision para extraer:

```
Prompt:
"Analiza el siguiente documento de mision y extrae la configuracion operativa.

Documento:
{document_text[:10000]}

Requisito del usuario:
{analysis_requirement}

Extrae JSON:
{
    "mission_type": "offense|defense|stability|recon|humanitarian|...",
    "mission_statement": "mision reformulada en formato estandar (Quien, Que, Cuando, Donde, Por que)",
    "commander_intent": "intencion del comandante (objetivo, estado final deseado, riesgos aceptables)",
    "constraints": ["ROE 1...", "Tiempo limite...", "Restriccion politica..."],
    "key_terrain": ["terreno critico 1...", "terreno critico 2..."],
    "priority_intel_requirements": ["PIR 1...", "PIR 2...", "PIR 3..."],
    "urgency": "routine|priority|immediate|flash",
    "time_horizon_hours": 24-720,
    "reasoning": "breve explicacion de como se clasifico la mision"
}"
```

**Criterio de aceptacion**:
- LLM extrae mission_statement coherente con el documento.
- Constraints incluyen ROE si el documento las menciona.
- PIRs son preguntas especificas de inteligencia, no genericas.

---

### T4.3 — Generar configuracion de fases adaptada al tipo de mision

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_config_generator.py`

**Descripcion**:
LLM ajusta los parametros de las fases MDMP segun la urgencia y tipo de mision:

- **Mision rutinaria**: max_rounds altos (3-5 por fase), deliberacion exhaustiva
- **Mision inmediata**: max_rounds bajos (1-2 por fase), deliberacion rapida
- **Mision ofensiva**: mas rondas en COA Development y Wargaming
- **Mision defensiva**: mas rondas en IPB y posiciones de terreno
- **Mision humanitaria**: CIMIC tiene mas peso, RED team menos relevante

**Criterio de aceptacion**:
- Fases ajustadas a la urgencia (flash → deliberacion rapida).
- Tipo de mision influye en que fases son mas largas.
- Fallback rule-based si LLM falla (valores por defecto de T3.2).

---

### T4.4 — Generar criterios de evaluacion ponderados

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_config_generator.py`

**Descripcion**:
LLM genera los criterios de evaluacion y sus pesos para la Fase 5 (COA Comparison), basandose en el tipo de mision y las restricciones:

```
Ejemplo para mision ofensiva:
- Mission Success: 0.35
- Force Protection: 0.20
- Time Efficiency: 0.20
- Sustainability: 0.15
- Flexibility: 0.10

Ejemplo para mision humanitaria:
- Civilian Impact: 0.30
- Mission Success: 0.25
- Force Protection: 0.20
- Time Efficiency: 0.15
- Sustainability: 0.10
```

**Criterio de aceptacion**:
- Pesos suman 1.0.
- Criterios son relevantes al tipo de mision.
- El usuario puede override los pesos antes de ejecutar.

---

### T4.5 — Serializar configuracion completa a JSON

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_config_generator.py`

**Que hay ahora**:
Output es `simulation_config.json` con: `time_config`, `event_config`, `agent_configs[]`, `platform_config`.

**Que debe quedar**:
Output es `deliberation_config.json` con:

```json
{
    "simulation_id": "sim_xxx",
    "project_id": "proj_xxx",
    "graph_id": "graph_xxx",
    "mission_config": { "mission_type": "...", "mission_statement": "...", ... },
    "phases": [ { "phase_id": 1, "phase_name": "...", "max_rounds": 3, ... } ],
    "agents": [ { "agent_id": 0, "role_code": "CDR", ... } ],
    "evaluation_criteria": [ { "name": "...", "weight": 0.3 } ],
    "max_coas": 4,
    "wargame_depth": 3,
    "created_at": "ISO-8601"
}
```

**Criterio de aceptacion**:
- Archivo JSON valido y parseable.
- Contiene toda la informacion necesaria para `run_tactical_deliberation.py`.
- No contiene campos sociales (time_config con peak_hours, etc.).

---

## FASE 5 — Integracion Backend (Manager, Runner, IPC, Memory)

> **Objetivo**: Adaptar los servicios de orquestacion para que lancen y monitoreen la deliberacion tactica en vez de la simulacion OASIS.
> **Archivos**: `simulation_manager.py`, `simulation_runner.py`, `simulation_ipc.py`, `zep_graph_memory_updater.py`, `action_logger.py`
> **Esfuerzo estimado**: Medio — modificaciones moderadas, no reescrituras completas.
> **Dependencias**: Fases 1-4 completadas.

---

### T5.1 — Adaptar `simulation_manager.py` — pipeline de preparacion

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_manager.py`

**Cambios**:
- Eliminar `enable_twitter`, `enable_reddit`, `twitter_status`, `reddit_status` de toda la clase.
- `prepare_simulation()`:
  - Llamar a `TacticalAgentGenerator` en vez de `OasisProfileGenerator`.
  - Llamar a config generator adaptado para generar `deliberation_config.json`.
  - Output: `agents.json` + `deliberation_config.json` (no CSV de Twitter ni JSON de Reddit).
- Añadir campos: `current_phase`, `current_phase_name`, `coa_count`, `deliberation_status`.
- Status del prepare: reportar progreso como "Leyendo entidades (0-20%) → Generando agentes tacticos (20-60%) → Generando config de deliberacion (60-90%) → Preparando scripts (90-100%)".

**Criterio de aceptacion**:
- `prepare_simulation()` genera `agents.json` con 10 agentes y `deliberation_config.json`.
- No genera archivos CSV de Twitter ni JSON de Reddit.
- El progreso se reporta correctamente al frontend.

---

### T5.2 — Adaptar `simulation_runner.py` — lanzar deliberacion

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_runner.py`

**Cambios**:
- Cambiar script de subprocess: de `run_parallel_simulation.py` a `run_tactical_deliberation.py`.
- Monitorear `deliberation/actions.jsonl` (un solo archivo, no `twitter/actions.jsonl` + `reddit/actions.jsonl`).
- Parsear acciones tacticas (fase, ronda, role, action_type) en vez de acciones sociales (CREATE_POST, LIKE_POST).
- Status: reportar `{current_phase, phase_name, phase_round, total_actions, coas_proposed, latest_action}`.
- Eliminar logica de "dos plataformas corriendo en paralelo".

**Criterio de aceptacion**:
- `start_simulation()` lanza `run_tactical_deliberation.py` como subprocess.
- El monitor lee `actions.jsonl` y actualiza `run_state.json` con fase actual.
- `run_state.json` contiene campos tacticos, no sociales.

---

### T5.3 — Adaptar `simulation_ipc.py` — comandos de control

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_ipc.py`

**Mantener**: `INTERVIEW`, `BATCH_INTERVIEW`, `CLOSE_ENV` (funcionan igual conceptualmente).

**Anadir**:
- `INJECT_INTEL`: Inyectar una pieza de inteligencia nueva a mitad de deliberacion (ej: "nueva informacion: el enemigo movio su QRF al norte"). El motor la incorpora en la siguiente ronda.
- `REDIRECT_PHASE`: Forzar salto a una fase especifica (ej: volver a Wargaming si se descubre nueva amenaza).
- `PAUSE_DELIBERATION` / `RESUME_DELIBERATION`: Pausar y reanudar.

**Criterio de aceptacion**:
- Los comandos IPC son procesados por `run_tactical_deliberation.py`.
- `INJECT_INTEL` aparece en el historial de deliberacion como nueva inteligencia.
- `REDIRECT_PHASE` cambia la fase actual sin perder el historial.

---

### T5.4 — Adaptar `zep_graph_memory_updater.py` — episodios de deliberacion

`[x]` **DONE**

**Archivo**: `backend/app/services/zep_graph_memory_updater.py`

**Que hay ahora**:
Convierte acciones sociales a lenguaje natural para alimentar el grafo:
- `CREATE_POST` → "发布了一条帖子：「内容」"
- `LIKE_POST` → "点赞了某人的帖子"
- `REPOST` → "转发了某人的帖子"
- Buffers separados por plataforma (twitter/reddit).

**Que debe quedar**:
Convertir acciones tacticas a episodios del grafo:
- `PROPOSE_COA` → "S3 MAJ Rodriguez proposed COA-2 'Northern Approach': maneuver 1st Platoon via Route Alpha to Objective Lion..."
- `EVALUATE_RISK` → "S4 CPT Chen assessed logistics risk of COA-2 as HIGH: supply route crosses contested terrain..."
- `CHALLENGE_ASSUMPTION` → "RED Team LTC Black challenged assumption that enemy QRF response time >2 hours..."
- `DECIDE_COA` → "CDR COL Mitchell selected COA-2 as the course of action. Rationale: ..."
- Un solo buffer (no hay plataformas multiples).

**Criterio de aceptacion**:
- Cada accion de deliberacion genera un episodio en el grafo.
- El grafo se enriquece durante la deliberacion (no solo al final).
- Consultas al grafo post-deliberacion devuelven tanto datos del documento original como decisiones tomadas.

---

### T5.5 — Adaptar `action_logger.py` — formato tactico

`[x]` **DONE**

**Archivo**: `backend/scripts/action_logger.py`

**Que hay ahora**:
```json
{"round": 5, "agent_id": 12, "agent_name": "张三", "action_type": "CREATE_POST", "action_args": {"content": "..."}}
```

**Que debe quedar**:
```json
{
    "phase": 3,
    "phase_name": "COA Development",
    "round": 2,
    "timestamp": "2026-03-18T14:23:01Z",
    "agent_id": 3,
    "agent_role": "S3",
    "agent_name": "MAJ Rodriguez",
    "action_type": "PROPOSE_COA",
    "content": "COA-2 Northern Approach: Move 1st Plt via Route Alpha...",
    "references": ["uuid-threat-1", "uuid-route-alpha"],
    "confidence": 0.85,
    "risk_assessment": "medium",
    "addressed_to": "ALL"
}
```

**Criterio de aceptacion**:
- Formato JSONL con campos tacticos (phase, agent_role, confidence, risk_assessment).
- Sin campos sociales (platform, action_args con content de tweet).
- Parseable por `simulation_runner.py` para monitoreo.

---

### T5.6 — Eliminar dependencia de OASIS/camel-ai

`[x]` **DONE**

**Archivos afectados**: `requirements.txt` o `pyproject.toml`, todos los imports de `oasis`

**Cambios**:
- Eliminar `camel-ai[all]` o `oasis` de las dependencias.
- Eliminar imports: `from oasis import ActionType, LLMAction, ManualAction, generate_twitter_agent_graph, generate_reddit_agent_graph`.
- Eliminar `backend/scripts/run_twitter_simulation.py`.
- Eliminar `backend/scripts/run_reddit_simulation.py`.
- Eliminar `backend/scripts/run_parallel_simulation.py`.
- Verificar que ningun otro archivo importa de OASIS.

**Criterio de aceptacion**:
- `pip install` no descarga OASIS ni camel-ai.
- Ningun archivo del proyecto importa de `oasis`.
- Los scripts eliminados no son referenciados en ningun otro lugar.

---

### T5.7 — Actualizar modelo de Simulation en `simulation_manager.py`

`[x]` **DONE**

**Archivo**: `backend/app/services/simulation_manager.py` (modelo interno de simulacion)

**Eliminar campos**:
- `enable_twitter`, `enable_reddit`
- `twitter_status`, `reddit_status`
- `twitter_runner_id`, `reddit_runner_id`
- `twitter_current_round`, `reddit_current_round`

**Anadir campos**:
- `current_phase`: int (1-7)
- `current_phase_name`: str
- `deliberation_status`: str ("analyzing" | "developing_coas" | "wargaming" | "comparing" | "deciding" | "producing_orders")
- `coas_proposed`: int
- `coa_selected`: Optional[int]
- `total_deliberation_actions`: int

**Criterio de aceptacion**:
- El estado de la simulacion refleja el progreso de deliberacion, no de redes sociales.
- El frontend puede mostrar en que fase MDMP esta el sistema.

---

## FASE 6 — Report Agent Adaptado

> **Objetivo**: Reescribir los prompts del Report Agent para que genere un informe tactico (estructura OPORD) en vez de un analisis de opinion publica.
> **Archivo principal**: `backend/app/services/report_agent.py`
> **Esfuerzo estimado**: Medio — la arquitectura ReACT se mantiene, solo cambian prompts y estructura de secciones.
> **Dependencias**: Fases 1-5 completadas (necesita datos de deliberacion para generar reporte).

---

### T6.1 — Reescribir prompt de planificacion de secciones

`[x]` **DONE**

**Archivo**: `backend/app/services/report_agent.py`

**Que hay ahora**:
El agente LLM planifica secciones de reporte de opinion publica: tendencias de sentimiento, influencers clave, narrativas dominantes, prediccion de evolucion.

**Que debe quedar**:
Nueva estructura de secciones:

```
1. Executive Summary
   → Brief de decision de una pagina: situacion, mision, COA recomendado, riesgo principal

2. Mission Analysis
   → Mision reformulada, tareas especificas/implicitas, restricciones, asunciones

3. Intelligence Assessment
   → Amenazas identificadas, COAs enemigos, analisis de terreno (del IPB)

4. Courses of Action Developed
   → Descripcion de cada COA con esquema de maniobra, organizacion de fuerzas

5. Wargaming Results
   → Resultados por COA, puntos de decision criticos, vulnerabilidades descubiertas

6. COA Comparison Matrix
   → Tabla de puntuacion con criterios ponderados (de la Fase 5)

7. Risk Assessment
   → Matriz de riesgo por COA (probabilidad x severidad), mitigaciones propuestas

8. Staff Recommendation
   → Recomendacion del staff con justificacion, COA seleccionado por el CDR

9. Dissenting Views
   → Desacuerdos significativos de la deliberacion (especialmente del RED Team)

10. Information Gaps
    → PIRs no respondidos, asunciones que requieren validacion, inteligencia faltante
```

**Criterio de aceptacion**:
- El agente genera las 10 secciones.
- Cada seccion cita datos del grafo y de la deliberacion.
- La COA Comparison Matrix es una tabla con numeros, no solo texto.

---

### T6.2 — Adaptar tools del Report Agent para contexto tactico

`[x]` **DONE**

**Archivo**: `backend/app/services/report_agent.py` (o `zep_tools.py`)

**Que se mantiene**:
- `InsightForge`: funciona sin cambios — busca en el grafo por semantica.
- `PanoramaSearch`: funciona sin cambios — vista completa del grafo.
- `QuickSearch`: funciona sin cambios — busqueda rapida.

**Que se adapta**:
- `InterviewAgents`: En vez de entrevistar agentes de redes sociales, entrevista a los agentes del Estado Mayor post-deliberacion.
  - Prompt cambia de "que publicaste en redes" a "cual fue tu evaluacion del COA-2 y por que".
  - El agente responde en caracter (ej: S4 responde desde perspectiva logistica).

**Que se anade**:
- `ReadDeliberationLog`: Nueva herramienta que lee `actions.jsonl` y filtra por fase/agente/tipo de accion.
- `GetCOAMatrix`: Herramienta que retorna la matriz de comparacion de COAs de la Fase 5.

**Criterio de aceptacion**:
- Report Agent puede acceder tanto al grafo como al log de deliberacion.
- Las citas en el reporte referencian entidades del grafo Y entradas de deliberacion.

---

### T6.3 — Adaptar chat post-reporte para preguntas tacticas

`[x]` **DONE**

**Archivo**: `backend/app/services/report_agent.py` (endpoint `/api/report/chat`)

**Que hay ahora**:
Chat responde preguntas sobre opinion publica: "cual fue el sentimiento dominante", "quienes fueron los influencers clave".

**Que debe quedar**:
Chat responde preguntas tacticas con trazabilidad:

```
Usuario: "Por que se descarto el COA-1?"
→ Report Agent busca en deliberation log: acciones SCORE_COA y DISSENT sobre COA-1
→ Respuesta: "COA-1 fue descartado porque:
   - S4 evaluo riesgo logistico como CRITICO (ronda 2, fase 4): la ruta de suministro cruza 3km de terreno contestado
   - RED Team identifico vulnerabilidad en el flanco sur (ronda 3, fase 4): el enemigo podria desplegar QRF en <45 min
   - Score total: 5.2/10 vs 7.8/10 del COA-2 seleccionado
   Fuentes: [Threat:IED_Cluster_Alpha], [Route:MSR_Tampa]"

Usuario: "Que pasa si el enemigo refuerza la posicion norte?"
→ InsightForge busca amenazas en Location "norte"
→ Cruza con wargaming del COA seleccionado
→ Respuesta: "Segun el wargaming de Fase 4, un refuerzo enemigo en el norte reduce P(exito) del COA-2 de 0.78 a ~0.52.
   El RED Team (LTC Black) ya considero este escenario en ronda 3: 'Si el enemigo refuerza Hill 203, la aproximacion norte pierde su ventaja de sorpresa.'
   Mitigacion propuesta por FSO: 'Fuego preparatorio de 120mm sobre Hill 203 antes del asalto.'
   Recomendacion: activar el plan de contingencia B (aproximacion por el este)."
```

**Criterio de aceptacion**:
- Las respuestas citan fases y rondas especificas de la deliberacion.
- Las respuestas incluyen referencias a entidades del grafo.
- Preguntas "what-if" usan datos del wargaming para proyectar escenarios.

---

### T6.4 — Actualizar preguntas pre-populadas de entrevista

`[x]` **DONE**

**Archivo**: `backend/app/services/report_agent.py` y/o frontend `Step5Interaction.vue`

**Que hay ahora**:
Preguntas de entrevista de redes sociales: "que publicaste", "que te parecio el contenido viral", "como interactuaste".

**Que debe quedar**:
Preguntas tacticas pre-populadas:

```
Para CDR:
- "Cual fue el factor determinante en su decision de COA?"
- "Que riesgo le preocupa mas del COA seleccionado?"

Para S2:
- "Cual es la amenaza mas probable y mas peligrosa?"
- "Que lagunas de inteligencia le preocupan mas?"

Para RED:
- "Si fuera el comandante enemigo, como explotaria las debilidades del COA seleccionado?"
- "Que asuncion de nuestro plan es mas fragil?"

Para S4:
- "Cuanto tiempo podemos sostener la operacion con los recursos actuales?"
- "Cual es el punto critico de logistica que podria hacer fallar el plan?"
```

**Criterio de aceptacion**:
- Al menos 2 preguntas pre-populadas por rol.
- Las preguntas son relevantes a la funcion del rol.
- El agente responde en caracter con datos de la deliberacion.

---

## FASE 7 — API y Frontend

> **Objetivo**: Adaptar los endpoints de la API de simulacion y los componentes del frontend para reflejar el nuevo flujo tactico.
> **Archivos**: `backend/app/api/simulation.py`, `frontend/src/components/Step*.vue`, `frontend/src/components/GraphPanel.vue`
> **Esfuerzo estimado**: Medio — cambios de labels, eliminacion de logica dual Twitter/Reddit, nuevo stepper de fases.
> **Dependencias**: Fases 1-6 completadas.

---

### T7.1 — Adaptar `/api/simulation/create` — eliminar plataformas

`[x]` **DONE**

**Archivo**: `backend/app/api/simulation.py`

**Cambios**:
- Eliminar parametros `enable_twitter`, `enable_reddit` del request body.
- Anadir parametro opcional `mission_type` (string, para pre-configurar fases).
- Response: eliminar `enable_twitter`/`enable_reddit`, anadir `deliberation_mode: true`.

---

### T7.2 — Adaptar `/api/simulation/start` y `/api/simulation/run-status`

`[x]` **DONE**

**Archivo**: `backend/app/api/simulation.py`

**`/start`**:
- Eliminar parametro `platform`.
- Anadir parametro `enable_graph_memory_update` (boolean, default true).
- Lanzar `run_tactical_deliberation.py` en vez de `run_parallel_simulation.py`.

**`/run-status`**:
- Eliminar: `twitter_running`, `reddit_running`, `twitter_current_round`, `reddit_current_round`.
- Anadir: `current_phase` (1-7), `current_phase_name`, `phase_round`, `total_actions`, `coas_proposed`, `deliberation_complete`.
- `recent_actions` cambia de acciones sociales a acciones tacticas.

---

### T7.3 — Adaptar `Step1GraphBuild.vue` — labels y texto

`[x]` **DONE**

**Archivo**: `frontend/src/components/Step1GraphBuild.vue`

**Cambios de texto** (solo labels, no logica):
- "模拟需求" (Requisito de simulacion) → "任务分析需求" (Requisito de analisis de mision)
- "上传新闻文档" (Subir documento de noticias) → "上传任务文档" (Subir documento de mision)
- "舆论模拟" (Simulacion de opinion) → "战术决策支持" (Soporte a decisiones tacticas)
- Descripcion: "上传OPORD、情报报告、地形分析等文档" (Subir OPORD, informes de inteligencia, analisis de terreno)

**Criterio de aceptacion**: Ningun texto hace referencia a redes sociales o opinion publica.

---

### T7.4 — Reescribir `Step2EnvSetup.vue` — agentes tacticos

`[x]` **DONE**

**Archivo**: `frontend/src/components/Step2EnvSetup.vue`

**Que hay ahora**:
- Toggle para habilitar Twitter/Reddit.
- Cards de agentes con: username, bio, karma, followers, MBTI, interested_topics.
- Selector de tipos de entidad a incluir.

**Que debe quedar**:
- Eliminar toggle Twitter/Reddit.
- Cards de agentes muestran: `role_code`, `role_name`, `rank`, `name`, `specialty`, `risk_tolerance`, `assigned_entity_types`, numero de entidades asignadas.
- Vista de "Estado Mayor" con los 10 roles en formato tabla o grid.
- Cada card muestra las entidades del grafo asignadas a ese agente.
- Configuracion editable: pesos de criterios de evaluacion, max_coas, wargame_depth.

**Criterio de aceptacion**:
- El usuario ve los 10 agentes con sus roles militares.
- Las entidades asignadas son visibles por agente.
- No hay referencias a Twitter, Reddit, karma, MBTI.

---

### T7.5 — Reescribir `Step3Simulation.vue` — stepper de deliberacion

`[x]` **DONE**

**Archivo**: `frontend/src/components/Step3Simulation.vue`

**Que hay ahora**:
- Dos barras de progreso: Twitter y Reddit (rondas completadas / total).
- Feed en tiempo real de acciones sociales (posts, likes, reposts).
- Toggle entre plataformas.

**Que debe quedar**:
- **Stepper horizontal de 7 fases MDMP**: Mission Analysis → IPB → COA Dev → Wargaming → COA Comparison → Decision → Orders.
  - La fase actual resaltada, fases completadas con checkmark.
  - Tooltip por fase mostrando: rondas completadas, acciones en esta fase.
- **Feed de deliberacion** en tiempo real:
  - Cada entrada muestra: `[S3 MAJ Rodriguez] PROPOSE_COA: "COA-2 Northern Approach..."` con badge de confidence (0.85) y risk (medium).
  - Filtros por rol de agente y tipo de accion.
- **Panel lateral "COA Tracker"**:
  - Lista de COAs propuestos con nombre y score parcial.
  - Se actualiza en tiempo real conforme avanza la deliberacion.

**Criterio de aceptacion**:
- El stepper refleja la fase actual de la deliberacion.
- El feed muestra acciones tacticas en tiempo real.
- El COA Tracker muestra los COAs propuestos y sus scores.

---

### T7.6 — Adaptar `Step5Interaction.vue` — entrevistas tacticas

`[x]` **DONE**

**Archivo**: `frontend/src/components/Step5Interaction.vue`

**Cambios**:
- Selector de agente muestra: `[CDR] COL Mitchell`, `[S2] MAJ Thompson`, etc. (en vez de nombres de usuario de redes sociales).
- Preguntas pre-populadas tacticas (de T6.4).
- Labels adaptados: "Entrevistar agente" → "Consultar miembro del Estado Mayor".

---

### T7.7 — Adaptar `GraphPanel.vue` — colores y iconos militares

`[x]` **DONE**

**Archivo**: `frontend/src/components/GraphPanel.vue`

**Cambios**:
- Paleta de colores de nodos por tipo de entidad militar:
  | Tipo | Color sugerido | Icono |
  |------|:----:|-------|
  | MilitaryUnit | Azul (#2563EB) | Escudo |
  | Threat | Rojo (#DC2626) | Triangulo alerta |
  | Asset | Verde (#16A34A) | Engranaje |
  | Location | Gris (#6B7280) | Pin |
  | Objective | Amarillo (#CA8A04) | Estrella |
  | Route | Naranja (#EA580C) | Flecha |
  | SupplyPoint | Verde claro (#4ADE80) | Caja |
  | TerrainFeature | Marron (#92400E) | Montana |
  | CivilianEntity | Morado (#9333EA) | Persona |
  | Organization | Gris oscuro (#374151) | Edificio |

- Detail panel de nodo: mostrar atributos tacticos relevantes (grid_reference, threat_type, etc.).
- Detail panel de edge: mostrar relacion tactica (THREATENS, SUPPORTS, LOCATED_AT, etc.).

**Criterio de aceptacion**:
- Los nodos del grafo tienen colores distintos por tipo de entidad militar.
- El panel de detalle muestra informacion tactica, no social.

---

## FASE 8 — Testing y Validacion

> **Objetivo**: Verificar que el sistema completo funciona end-to-end con documentos militares reales.
> **Esfuerzo estimado**: Alto — requiere documentos de prueba y evaluacion de calidad.
> **Dependencias**: Todas las fases anteriores completadas.

---

### T8.1 — Crear documento OPORD de prueba

`[ ]` **TODO**

**Descripcion**:
Crear un documento OPORD ficticio pero realista para testing. Debe incluir:
- Situacion (fuerzas enemigas, fuerzas propias, terreno)
- Mision
- Ejecucion (concepto de la operacion)
- Sostenimiento
- Mando y senales

El documento debe ser lo suficientemente complejo para generar al menos 30 entidades en el grafo y relaciones significativas entre ellas.

**Criterio de aceptacion**:
- Documento de al menos 3 paginas.
- Contiene entidades de al menos 6 de los 10 tipos definidos.
- Contiene relaciones explicitas e implicitas entre entidades.

---

### T8.2 — Test E2E: Upload → Graph → Agents → Deliberation → Report → Chat

`[ ]` **TODO**

**Descripcion**:
Ejecutar el flujo completo:
1. Subir OPORD de prueba via `/api/graph/ontology/generate`.
2. Construir grafo via `/api/graph/build`.
3. Verificar que el grafo contiene entidades militares (no sociales).
4. Crear simulacion y preparar agentes via `/api/simulation/create` + `/api/simulation/prepare`.
5. Verificar que se generan 10 agentes con roles del Estado Mayor.
6. Ejecutar deliberacion via `/api/simulation/start`.
7. Verificar que pasa por las 7 fases MDMP.
8. Verificar que genera al menos 2 COAs distintos.
9. Generar reporte via `/api/report/generate`.
10. Verificar que el reporte tiene las 10 secciones tacticas.
11. Hacer preguntas via `/api/report/chat`.
12. Verificar que las respuestas citan datos del grafo y de la deliberacion.

**Criterio de aceptacion**:
- Todo el flujo completa sin errores.
- Las entidades del grafo son militares.
- Los COAs son tacitamente plausibles y diferentes entre si.
- El reporte tiene estructura de OPORD.
- El chat responde con trazabilidad.

---

### T8.3 — Test de calidad: evaluacion de COAs generados

`[ ]` **TODO**

**Descripcion**:
Evaluar cualitativamente la calidad de los COAs generados:
- ¿Son genuinamente diferentes? (no variaciones menores del mismo plan)
- ¿Son tacticamente plausibles? (no proponen cosas imposibles)
- ¿Consideran las restricciones del documento? (ROE, tiempo, recursos)
- ¿El Red Team identifica vulnerabilidades reales?
- ¿La matriz de comparacion tiene puntuaciones razonables?

**Criterio de aceptacion**:
- Al menos 2 de 3 COAs generados son tacticamente plausibles.
- Los COAs difieren en al menos uno de: eje de avance, timing, organizacion de fuerzas.
- El Red Team identifica al menos una vulnerabilidad real por COA.

---

### T8.4 — Test de regresion: verificar que Fases 1-2 del workflow (Graph Build) siguen funcionando

`[ ]` **TODO**

**Descripcion**:
Verificar que el cambio de ontologia no rompe el flujo de construction de grafos:
- Zep acepta los 10 nuevos entity types.
- Zep acepta los 10 nuevos edge types.
- Los episodios se procesan correctamente.
- La paginacion sigue funcionando.
- InsightForge, PanoramaSearch y QuickSearch retornan resultados relevantes.

**Criterio de aceptacion**:
- Grafo se construye sin errores.
- Busqueda semantica retorna entidades militares relevantes.
- La paginacion no se rompe con los nuevos tipos.

---

## Riesgos y Mitigaciones

| # | Riesgo | Probabilidad | Impacto | Mitigacion |
|:-:|--------|:------------:|:-------:|-----------|
| R1 | **Calidad del razonamiento militar del LLM** — Los LLMs consumer (GPT-4o, Claude) pueden producir analisis tactico generico o incorrecto | Alta | Alto | Prompts detallados con referencias doctrinales (FM 5-0, ATP 5-0.1). Considerar RAG sobre manuales militares como documentos adicionales en el grafo. |
| R2 | **Coherencia de deliberacion** — El historial acumulado entre fases puede exceder la ventana de contexto del LLM | Media | Alto | Sumarizacion obligatoria entre fases (T3.8). Max 500 tokens por resumen de fase. Solo historial completo de fase actual. |
| R3 | **COAs demasiado similares** — El sistema genera variaciones menores en vez de COAs genuinamente diferentes | Alta | Medio | Prompt de `PROPOSE_COA` fuerza diferencias estructurales: "Cada COA debe diferir en AL MENOS uno de: eje de avance, timing, organizacion de fuerzas, uso de fuegos." |
| R4 | **Red Team inefectivo** — El agente adversario no challenge realmente los COAs | Media | Medio | Prompt especifico que recompensa identificar debilidades. Persona del RED tiene `risk_tolerance: 0.8` y `doctrinal_adherence: 0.3` (pensamiento no convencional). |
| R5 | **Limite de Zep** — Max 10 entity types y 10 edge types puede ser insuficiente para escenarios complejos | Baja | Medio | Ontologia disenada para caber en el limite. Atributos custom dan flexibilidad dentro de cada tipo. |
| R6 | **Clasificacion de informacion** — Documentos militares reales pueden ser clasificados | Alta | Critico | Sistema debe correr **on-premise**. Considerar LLMs locales (Llama 3, Mistral) en vez de APIs cloud. Zep self-hosted disponible. |
| R7 | **Costo de LLM** — 7 fases x multiples rondas x 10 agentes = muchas llamadas LLM | Media | Medio | Semaforo de concurrencia (como el actual `semaphore=30`). Considerar modelos mas baratos para fases simples (Comparison, Orders). |

---

## Componentes que se Reutilizan sin Cambios

Estos archivos **NO requieren modificacion**. Se mantienen exactamente como estan:

| Archivo | Funcion | Por que no cambia |
|---------|---------|-------------------|
| `backend/app/services/graph_builder.py` | Construir grafo en Zep | API de Zep es domain-agnostic |
| `backend/app/services/zep_entity_reader.py` | Leer entidades del grafo | Filtra por labels, no por contenido |
| `backend/app/services/zep_tools.py` (InsightForge, PanoramaSearch, QuickSearch) | Busqueda semantica en el grafo | Consultas genericas, no asumen dominio |
| `backend/app/services/text_processor.py` | Chunking de texto | Completamente generico |
| `backend/app/utils/file_parser.py` | Parsear PDF/TXT/MD | Completamente generico |
| `backend/app/utils/zep_paging.py` | Paginacion de nodos/edges | API de Zep, generico |
| `backend/app/utils/llm_client.py` | Cliente LLM (OpenAI SDK) | Generico |
| `backend/app/utils/logger.py` | Logging | Generico |
| `backend/app/models/project.py` | Modelo de proyecto | Ciclo de vida identico |
| `backend/app/models/task.py` | Modelo de tarea async | Tracking generico |
| `backend/app/api/graph.py` | API de grafos | Endpoints genericos |
| `backend/app/api/report.py` | API de reportes | Endpoints genericos |
| `frontend/src/api/index.js` | Axios + retry | Infra generica |
| `frontend/src/api/graph.js` | API client grafos | Generico |
| `frontend/src/api/report.js` | API client reportes | Generico |

---

> **Nota**: Este documento es un registro vivo. Actualizar los marcadores `[ ]` → `[~]` → `[x]` conforme se avanza. Actualizar la tabla de "Progreso por Fase" y el contador global al completar cada tarea.
