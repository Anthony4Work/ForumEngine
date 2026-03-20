# Plan: Sistema Hibrido — Agentes SME en Deliberacion + Feedback Loop OASIS

**Fecha**: 2026-03-19
**Estado**: Propuesta / Pendiente de implementacion
**Autor**: Anthony + Claude Opus 4.6

---

## 1. Motivacion y Contexto

### Problema actual

El sistema de deliberacion tactica MDMP tiene **10 agentes fijos** (oficiales militares) que razonan sobre entidades del knowledge graph como datos pasivos:

- Cada agente ve **maximo 20 entidades** resumidas en **~200 caracteres cada una**
- Las entidades son texto estatico inyectado en el prompt, no participantes activos
- Solo 10 perspectivas fijas analizan todo el battlespace
- La unica forma de acceder a mas informacion es `request_intel` (busqueda Graphiti), que devuelve facts desconectados del contexto

### Que teniamos con OASIS (legacy)

El sistema OASIS podia crear **cientos/miles de agentes** desde entidades del grafo:

- Cada entidad se convertia en un agente con persona rica (~2000 chars)
- Enriquecimiento profundo via Graphiti: busqueda 2-pass (edges + nodes), retry con backoff
- Los agentes interactuaban entre si en una plataforma simulada (Reddit/Twitter)
- Escalaba a miles de agentes con concurrencia controlada

### Oportunidad

Combinar la **estructura de deliberacion** del MDMP con la **riqueza de agentes** de OASIS en un sistema hibrido:

1. **Componente A**: Entidades del grafo se convierten en "expertos locales" (SME) que participan activamente en la deliberacion
2. **Componente B**: Tras decidir un curso de accion (COA), simular la reaccion publica/social con OASIS como feedback loop

---

## 2. Componente A: Agentes SME (Subject Matter Experts)

### 2.1. Concepto

Las entidades mas relevantes del knowledge graph se convierten en **testigos/expertos locales** que participan junto a los 10 oficiales. No dan analisis doctrinal — aportan **conocimiento directo y local**.

**Ejemplo**: En un escenario con una aldea en zona de conflicto:
- S2 (inteligencia) analiza la amenaza desde doctrina militar
- Un SME "Elder Ahmad" (entidad CivilianEntity del grafo) aporta: "Las patrullas enemigas pasan cada martes por la ruta norte, los aldeanos ya no usan ese camino"
- Esa informacion de terreno NO esta en el resumen de 200 chars que S2 ve actualmente

### 2.2. Seleccion inteligente de entidades para SME

**Tarea**: Crear algoritmo de scoring para seleccionar las N entidades mas valiosas como SME.

**Criterios de puntuacion**:

| Criterio | Peso | Logica |
|----------|------|--------|
| Conectividad en grafo | 40% | Mas edges/nodes relacionados = mas conocimiento para compartir |
| Relevancia de tipo | 30% | CivilianEntity, personas, lideres locales, ONGs puntuan alto. Tipos ya cubiertos por staff (MilitaryUnit→S3) puntuan bajo |
| Diversidad | 30% | Bonus por tipos no representados aun en la seleccion |

**Exclusiones**: Entidades abstractas como `Objective` o `Route` que ya estan cubiertas por los oficiales.

**Output**: Top N entidades (configurable, default 5-8)

### 2.3. Generacion de persona SME

**Tarea**: Crear generador que reutilice infraestructura existente de OASIS.

**Reutilizar de `oasis_profile_generator.py`**:
- `_search_graphiti_for_entity()` (lineas 281-398): Busqueda 2-pass con ThreadPoolExecutor
  - Pass 1: Edge search (EDGE_HYBRID_SEARCH_RRF) → hasta 30 facts
  - Pass 2: Node search (NODE_HYBRID_SEARCH_RRF) → hasta 20 summaries
  - Timeout 30s, retry 3x con backoff
- `_build_entity_context()` (lineas 400-472): Combina atributos + edges + nodes + search results

**Prompt nuevo (NO reutilizar el de OASIS)**: Contexto militar, no redes sociales:

```
Eres un generador de personas para testigos/expertos locales (SME) que
proporcionaran testimonio de primera mano durante deliberaciones militares.

Entidad: {entity_name} ({entity_type})
Contexto del knowledge graph:
{graphiti_enriched_context}

Genera JSON con:
1. "name": nombre realista (mantener original si es persona)
2. "persona": 1500-2000 chars enfocado en:
   - Que sabe de primera mano (observaciones, NO analisis)
   - Su relacion con el area de operaciones
   - Su credibilidad y posibles sesgos
   - Tipo de preguntas que puede responder con autoridad
3. "specialty": area principal de conocimiento local
4. "expertise_tags": 3-5 tags tematicos
5. "credibility": 0-1 basado en posicion y acceso a informacion
```

### 2.4. Modelo de datos SME

**Tarea**: Nuevo dataclass `SMEAgentProfile`

```python
@dataclass
class SMEAgentProfile:
    agent_id: int               # 100+ para no colisionar con staff 0-9
    role_code: str              # "SME_001", "SME_002"
    role_name: str              # "Local Village Elder", "NGO Field Director"
    name: str
    specialty: str
    persona: str                # ~2000 chars (enriquecido via Graphiti)
    source_entity_uuid: str     # link al entity del grafo
    source_entity_type: str
    relevant_phases: List[int]  # fases donde participa
    expertise_tags: List[str]   # ["local_terrain", "civilian_population"]
    credibility: float          # 0-1
    is_sme: bool = True         # flag discriminador
```

**Diferencia clave con staff**: Sin perfil cognitivo militar (risk_tolerance, doctrinal_adherence, etc.). Los SME no son analistas doctrinales.

### 2.5. Asignacion de fases por tipo de entidad

| Tipo de Entidad | Fases donde participa | Justificacion |
|-----------------|----------------------|---------------|
| CivilianEntity, personas | 1, 3, 5 | Mission analysis, COA dev, COA comparison |
| Threat | 2, 4 | IPB, Wargaming |
| TerrainFeature, Location | 1, 2, 3 | Mission analysis, IPB, COA dev |
| Asset, SupplyPoint | 3, 4, 7 | COA dev, Wargaming, Orders |

**Nunca participan en**: Fase 6 (decision del CDR) ni Fase 7 (produccion ordenes) — esas son exclusivamente staff.

### 2.6. Nuevos action types

**Tarea**: Anadir a `TacticalActionType` en `run_tactical_deliberation.py`:

| Action | Quien lo usa | Descripcion |
|--------|-------------|-------------|
| `consult_sme` | Staff officers | Pregunta especifica a un SME |
| `sme_testimony` | SME agents | Respuesta a consulta o testimonio voluntario |

Anadir `consult_sme` a `valid_actions` de Fases 1-5.

### 2.7. Integracion en el loop de deliberacion

**Tarea**: Modificar `TacticalDeliberationEngine.run()` en `run_tactical_deliberation.py`

**Flujo por ronda**:

```
1. Primary staff officer actua (secuencial)
2. Resto de staff actuan (paralelo — ya implementado)
3. [NUEVO] Procesar SMEs:
   a. Si algun officer uso "consult_sme":
      → Matching: buscar SME con expertise_tags mas relevante
      → SME responde con _sme_act()
   b. Si no hubo consulta y hay SMEs activos en esta fase:
      → 1-2 SMEs pueden aportar testimonio voluntario
      → Probabilidad configurable (default 40% por SME elegible)
```

**Nuevos metodos**:
- `_build_sme_context(sme, phase, round, phase_log, question=None)`: Prompt que enfatiza "conocimiento personal directo, NO analisis militar"
- `_sme_act(sme, context)`: Llamada LLM con contexto SME
- `_match_sme_to_question(request, active_smes)`: Keyword matching entre consulta y expertise_tags

### 2.8. Preparacion en SimulationManager

**Tarea**: Nuevo paso en `prepare_simulation()` de `simulation_manager.py`

```
Stage 2b: Generate SME agents (si SME_AGENT_ENABLED=true)
  1. SMEAgentGenerator.generate_sme_agents(graph_id, entities, staff_assignments, mission_context)
  2. Merge resultado en agents.json con flag is_sme=True
  3. Actualizar state.profiles_count
```

---

## 3. Componente B: Feedback Loop OASIS Post-Decision

### 3.1. Concepto

Tras la Fase 6 (COA Decision), el sistema:
1. Extrae la decision del COA seleccionado
2. Lo convierte en un "evento publico" comprensible para civiles
3. Ejecuta una simulacion OASIS corta (30 rondas) donde todas las entidades del grafo reaccionan como agentes sociales
4. Resume la reaccion (sentimiento, preocupaciones, oposicion)
5. Opcionalmente alimenta una Fase 8 donde CIMIC y staff evaluan el impacto social

### 3.2. Extraccion de COA tras Fase 6

**Tarea**: En `run_tactical_deliberation.py`, tras completar Phase 6, guardar `coa_decision.json`:

```json
{
    "coa_id": 2,
    "coa_name": "COA-2",
    "description": "Descripcion completa del COA...",
    "proposed_by": "S3",
    "commander_guidance": "Intent del CDR...",
    "phase_summaries": {
        "1": "Resumen mision...",
        "2": "Resumen IPB...",
        ...
    }
}
```

### 3.3. Conversor COA → Eventos OASIS

**Tarea**: Nuevo archivo `backend/app/services/coa_to_oasis_converter.py`

Usa una llamada LLM para transformar el COA militar en contenido consumible por agentes sociales:

**Input**: `coa_decision.json` + resumenes de fases
**Output**:
1. **initial_posts** (2-3): Comunicado oficial, reportaje de noticias, rumor/especulacion
2. **scenario_injection**: Texto inyectado en cada persona OASIS ("NOTICIA: [evento]. Como te afecta a ti y tu comunidad?")

**Ejemplo de transformacion**:
- COA: "Establish checkpoint operations along Route Alpha with humanitarian corridor through Sector 4"
- Noticia: "Las autoridades militares han anunciado nuevos puntos de control en la Ruta Alpha. Se habilitara un corredor humanitario en el Sector 4 para garantizar el acceso de civiles."
- Rumor: "Dicen que van a cerrar la Ruta Alpha completamente. Los comerciantes estan preocupados por el suministro."

### 3.4. Runner OASIS simplificado

**Tarea**: Nuevo archivo `backend/scripts/run_oasis_feedback.py`

Version recortada de `run_reddit_simulation.py` optimizada para feedback rapido:

| Parametro | OASIS completo | Feedback runner |
|-----------|---------------|----------------|
| Rondas | 144+ | 30 (configurable) |
| Activacion de agentes | Por hora del dia | Todos activos desde inicio |
| Posts iniciales | Configurables | COA announcement posts |
| Modo IPC/entrevista | Si | No |
| Output | traces.db | traces.db + summary.json |

### 3.5. Resumidor de reaccion social

**Tarea**: Nuevo archivo `backend/app/services/social_reaction_summarizer.py`

Lee la DB SQLite de OASIS y produce analisis estructurado:

```python
class SocialReactionSummarizer:
    def summarize(self, db_path: str) -> dict:
        # 1. Queries SQLite: contar posts, comments, likes/dislikes
        # 2. LLM: clasificar sentimiento de cada post/comment
        # 3. LLM: extraer temas de oposicion y apoyo
        # 4. LLM: generar resumen narrativo de 500 palabras
        return {
            "total_posts": int,
            "total_comments": int,
            "sentiment_distribution": {"positive": %, "neutral": %, "negative": %},
            "key_concerns": ["preocupacion1", "preocupacion2"],
            "opposition_themes": [...],
            "support_themes": [...],
            "narrative_summary": "Resumen generado por LLM..."
        }
```

### 3.6. Fase 8 opcional: Social Impact Assessment

**Tarea**: Nueva fase condicional en `run_tactical_deliberation.py`

```python
PHASE_8_SOCIAL_IMPACT = {
    "phase_id": 8,
    "phase_name": "Social Impact Assessment",
    "description": "Revisar reaccion de la poblacion al COA seleccionado. Recomendar modificaciones si es necesario.",
    "max_rounds": 2,
    "active_roles": ["CDR", "XO", "CIMIC", "S2"],
    "primary_role": "CIMIC",
    "valid_actions": ["recommend", "evaluate_risk", "refine_coa", "concur", "dissent", "consult_sme"],
}
```

El resumen de reaccion social se inyecta como "Phase 7.5 summary" para que los oficiales lo vean en su contexto.

---

## 4. Particionamiento de entidades: SME vs OASIS Social

**Decision arquitectural**: Las mismas entidades pueden ser AMBOS tipos de agente. No son mutuamente excluyentes:

- **Como SME** (Componente A): 5-10 entidades top, persona militar/testigo, participan en fases 1-7
- **Como agente social** (Componente B): TODAS las entidades, persona redes sociales, participan en simulacion post-decision

La misma entidad "Elder Ahmad" puede ser:
- SME en deliberacion: aporta conocimiento local sobre patrullas enemigas
- Agente OASIS: publica en Reddit simulado su reaccion al anuncio del COA

Las personas se generan por separado para cada contexto.

---

## 5. Configuracion

### Nuevos parametros en `.env` y `config.py`

```
# Componente A: SME Agents
SME_AGENT_ENABLED=true          # Kill switch
SME_AGENT_COUNT=5               # Numero de SMEs a generar
SME_VOLUNTEER_PROBABILITY=0.4   # Probabilidad de testimonio voluntario por ronda

# Componente B: OASIS Feedback Loop
OASIS_FEEDBACK_ENABLED=false    # Desactivado por defecto (mas pesado)
OASIS_FEEDBACK_ROUNDS=30        # Rondas de simulacion social
OASIS_FEEDBACK_PLATFORM=reddit  # Plataforma a simular
OASIS_FEEDBACK_RUN_PHASE_8=true # Ejecutar fase de evaluacion de impacto
```

### Seccion en `deliberation_config.json`

```json
{
    "sme_config": {
        "enabled": true,
        "count": 5,
        "volunteer_probability": 0.4
    },
    "oasis_feedback_loop": {
        "enabled": false,
        "rounds": 30,
        "platform": "reddit",
        "run_phase_8": true
    }
}
```

---

## 6. Archivos a crear

| Archivo | Proposito |
|---------|-----------|
| `backend/app/services/sme_agent_generator.py` | Seleccion, scoring y generacion de SMEs |
| `backend/app/services/coa_to_oasis_converter.py` | Conversion COA → eventos OASIS |
| `backend/app/services/social_reaction_summarizer.py` | Analisis DB SQLite → resumen estructurado |
| `backend/scripts/run_oasis_feedback.py` | Runner OASIS simplificado para feedback |

## 7. Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `backend/app/config.py` | Params SME + OASIS feedback |
| `backend/app/services/tactical_agent_generator.py` | Dataclass SMEAgentProfile, serializacion mixta staff+SME |
| `backend/scripts/run_tactical_deliberation.py` | Action types SME, separar staff/SME, loop SME post-ronda, Phase 8, metodos contexto SME |
| `backend/app/services/simulation_manager.py` | Stage 2b: generar SMEs, config OASIS feedback |
| `backend/app/services/deliberation_config_generator.py` | Secciones sme_config y oasis_feedback_loop |

---

## 8. Flujo end-to-end completo

```
prepare_simulation()
  |-- Leer entidades del grafo
  |-- Generar 10 staff officers (existente)
  |-- [NUEVO] Generar N agentes SME desde entidades top
  |-- Generar config deliberacion (+ sme_config + oasis_feedback)
  |-- Guardar agents.json (staff + SMEs) + deliberation_config.json

run_tactical_deliberation.py
  |
  |-- Fases 1-5: Staff deliberan + SMEs participan
  |   |-- Cada ronda:
  |       |-- Primary officer actua (secuencial)
  |       |-- Resto de staff actuan (paralelo)
  |       |-- [NUEVO] SMEs: responden consultas o aportan testimonio
  |
  |-- Fase 6: CDR decide COA (solo staff)
  |-- Fase 7: Produccion de ordenes (solo staff)
  |
  |-- [NUEVO] Si OASIS_FEEDBACK_ENABLED:
  |   |-- Extraer COA decision → coa_decision.json
  |   |-- Convertir COA → eventos OASIS (LLM)
  |   |-- Generar perfiles OASIS para todas las entidades
  |   |-- Ejecutar simulacion Reddit/Twitter (30 rondas)
  |   |-- Resumir reaccion social → summary.json
  |   |-- Si OASIS_FEEDBACK_RUN_PHASE_8:
  |       |-- Fase 8: CIMIC lidera evaluacion de impacto social
  |       |-- Staff revisa reaccion y recomienda modificaciones al COA
  |
  |-- Guardar resultados finales
```

---

## 9. Estimacion de impacto en rendimiento

### Componente A (SMEs en deliberacion)

| Escenario | Llamadas LLM adicionales por ronda | Impacto |
|-----------|-------------------------------------|---------|
| Sin consultas, 0 voluntarios | +0 | Ninguno |
| 1 consulta SME | +1 | +3s |
| 2 voluntarios | +2 | +3s (paralelo con semaforo) |
| Max: 2 consultas + 2 voluntarios | +4 | +6s |

Con ~20 rondas totales y ~2 llamadas SME de media: **+40 llamadas LLM** (~2 min extra)

### Componente B (OASIS feedback)

| Fase | Llamadas LLM | Tiempo estimado |
|------|-------------|-----------------|
| Conversion COA → eventos | 1 | ~5s |
| Generacion perfiles OASIS (100 entidades) | ~100 | ~2 min (paralelo) |
| Simulacion 30 rondas | ~3000 | ~5-10 min (OASIS semaphore=30) |
| Resumen reaccion | ~3 | ~15s |
| Fase 8 (2 rondas, 4 agentes) | ~8 | ~30s |
| **Total** | **~3112** | **~8-13 min** |

---

## 10. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|--------|-----------|
| SMEs anaden ruido a la deliberacion | Probabilidad de voluntariado configurable + solo en fases relevantes |
| Context window se llena | Limite existente de 30 acciones en historial + testimonio SME max 300 chars |
| OASIS feedback es lento | Desactivado por defecto, rondas reducidas (30 vs 144) |
| Calidad de conversion COA→evento civil | Incluir resumenes de todas las fases como contexto para el LLM |
| Dependencia de libreria OASIS pesada | Componente B es 100% opcional y aislado |
| Rate limits del API con muchos agentes OASIS | OASIS ya usa semaphore=30, ajustable via LLM_MAX_CONCURRENT |

---

## 11. Para que sirve este update — Resumen ejecutivo

### Sin el hibrido (sistema actual):
- 10 oficiales razonan sobre resumenes de 200 chars de entidades
- Las entidades son datos pasivos, no pueden corregir suposiciones erroneas
- No hay forma de testear como reaccionara la poblacion a una decision
- El analisis esta limitado a 10 perspectivas doctrinales fijas

### Con el hibrido:
- **SMEs aportan ground truth**: Los oficiales pueden consultar "testigos" que conocen el terreno real, no solo resumenes
- **Deliberacion mas informada**: S2 pregunta al elder local sobre movimientos enemigos, CIMIC consulta al director de ONG sobre desplazados
- **Validacion social**: Antes de ejecutar un COA, se simula como reaccionara la poblacion. Si hay oposicion fuerte, se puede ajustar
- **Feedback loop cerrado**: Decision → Reaccion → Ajuste. No solo planificar, sino anticipar consecuencias
- **Escalable**: 5 SMEs para deliberacion rapida, 500 agentes OASIS para simulacion completa
- **Retrocompatible**: Todo desactivable via config. Con los flags en false, el sistema se comporta exactamente como antes
