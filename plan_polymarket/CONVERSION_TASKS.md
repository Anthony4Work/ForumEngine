# MiroFish → Polymarket Swarm Intelligence Bot
## Registro Completo de Tareas de Conversion

> **Ultima actualizacion**: 2026-03-18
> **Estado global**: En planificacion
> **Progreso**: 0 / 42 tareas completadas

---

### Leyenda de estados

| Icono | Estado | Significado |
|:-----:|--------|-------------|
| `[ ]` | **TO DO** | Pendiente de iniciar |
| `[~]` | **EN CURSO** | Trabajo iniciado, aun no completado |
| `[x]` | **COMPLETADO** | Tarea finalizada y verificada |
| `[!]` | **BLOQUEADO** | Depende de otra tarea o decision externa |

---

## FASE 0 — Setup de Infraestructura y Wallet Polymarket

> **Objetivo**: Tener una cuenta Polymarket operativa, las dependencias instaladas y la configuracion base del proyecto lista para que las fases posteriores puedan funcionar.
>
> **Prerequisito**: Ninguno
>
> **Entregable**: `.env` configurado con credenciales Polymarket, documentacion de setup completa

### 0.1 Documentacion de Setup

- [ ] **T-001** — Crear `docs/POLYMARKET_SETUP.md`
  - **Descripcion**: Guia paso a paso para configurar una cuenta Polymarket desde cero. Debe cubrir el flujo completo: creacion de wallet Polygon (MetaMask), registro en polymarket.com, proceso KYC (si aplica desde la jurisdiccion del usuario), obtencion de USDC.e en Polygon (bridge desde mainnet o compra directa), exportacion de la private key para `py-clob-client`, generacion de API credentials (L1 auth → L2 derivation), y configuracion final del `.env`.
  - **Archivo**: `docs/POLYMARKET_SETUP.md` (nuevo)
  - **Criterio de completado**: Un usuario sin cuenta Polymarket puede seguir la guia y terminar con un `.env` funcional
  - **Referencia tecnica**: Polymarket usa autenticacion en dos niveles: L1 firma EIP-712 con private key del wallet, L2 genera `apiKey`/`secret`/`passphrase` derivados. El SDK oficial `py-clob-client` necesita la private key para L1 y opcionalmente los credentials L2 para REST calls

### 0.2 Configuracion del Proyecto

- [ ] **T-002** — Anadir variables de entorno Polymarket a `backend/app/config.py`
  - **Descripcion**: Extender la clase `Config` (linea 20 de `config.py`) con todas las variables necesarias para el modulo Polymarket. Deben seguir el patron existente de `os.environ.get()` con defaults sensatos.
  - **Archivo a modificar**: `backend/app/config.py` (existente, 67 lineas)
  - **Ubicacion exacta**: Despues de la linea 56 (`REPORT_AGENT_TEMPERATURE`), antes de `validate()`
  - **Variables a anadir**:
    ```python
    # ============= Polymarket =============
    POLYMARKET_PRIVATE_KEY = os.environ.get('POLYMARKET_PRIVATE_KEY')
    POLYMARKET_API_KEY = os.environ.get('POLYMARKET_API_KEY')
    POLYMARKET_API_SECRET = os.environ.get('POLYMARKET_API_SECRET')
    POLYMARKET_PASSPHRASE = os.environ.get('POLYMARKET_PASSPHRASE')
    POLYMARKET_MODE = os.environ.get('POLYMARKET_MODE', 'paper')  # paper | live
    POLYMARKET_MAX_TRADE_USD = float(os.environ.get('POLYMARKET_MAX_TRADE_USD', '10'))
    POLYMARKET_MAX_BANKROLL_USD = float(os.environ.get('POLYMARKET_MAX_BANKROLL_USD', '200'))
    POLYMARKET_MIN_EDGE = float(os.environ.get('POLYMARKET_MIN_EDGE', '0.10'))
    POLYMARKET_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/polymarket')

    # ============= News Sources =============
    POLYMARKET_NEWS_RSS_FEEDS = os.environ.get('POLYMARKET_NEWS_RSS_FEEDS', '')
    NEWSAPI_KEY = os.environ.get('NEWSAPI_KEY', '')
    TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN', '')
    ```
  - **Criterio de completado**: `from app.config import Config; Config.POLYMARKET_MODE` retorna `'paper'`

- [ ] **T-003** — Actualizar `.env.example` con variables Polymarket
  - **Descripcion**: Anadir una seccion `# ===== Polymarket =====` al final de `.env.example` con todas las variables nuevas documentadas con comentarios explicativos.
  - **Archivo a modificar**: `.env.example` (existente, 16 lineas)
  - **Criterio de completado**: Un usuario que copie `.env.example` a `.env` ve todas las variables Polymarket con placeholders claros

- [ ] **T-004** — Anadir dependencias Python a `backend/requirements.txt`
  - **Descripcion**: Agregar las bibliotecas necesarias para el modulo Polymarket al archivo de requisitos existente.
  - **Archivo a modificar**: `backend/requirements.txt` (existente, 35 lineas)
  - **Dependencias a anadir**:
    ```
    # ============= Polymarket =============
    py-clob-client>=0.1.0        # SDK oficial Polymarket CLOB
    feedparser>=6.0.0            # Parsing de feeds RSS/Atom
    ```
  - **Nota**: `requests` ya esta disponible via Flask. `newsapi-python` es opcional (se puede usar `requests` directo). Twitter scraping se evalua en Fase 1.
  - **Criterio de completado**: `pip install -r backend/requirements.txt` instala sin errores

- [ ] **T-005** — Crear directorio `backend/app/services/polymarket/` con `__init__.py`
  - **Descripcion**: Crear el package Python que contendra todos los servicios del modulo Polymarket. El `__init__.py` exporta las clases principales para facilitar imports.
  - **Archivo nuevo**: `backend/app/services/polymarket/__init__.py`
  - **Contenido esperado**: Imports de los servicios principales (se iran anadiendo conforme se creen)
  - **Criterio de completado**: `from app.services.polymarket import *` no lanza error

---

## FASE 1 — Conexion a Polymarket + Ingestion de Datos + Ontologia Financiera

> **Objetivo**: Conectar a la API de Polymarket para leer datos de mercados, implementar un pipeline de ingestion de noticias multi-fuente (RSS, NewsAPI, web search, Twitter), crear la ontologia de dominio financiero, y tener un sistema de paper trading basico.
>
> **Prerequisito**: Fase 0 completada
>
> **Entregable**: Se puede consultar mercados Polymarket, recoger noticias sobre un evento, generar ontologia financiera, y construir un grafo Zep con entidades financieras

### 1.1 Connector de Polymarket

- [ ] **T-006** — Crear `backend/app/services/polymarket/connector.py`
  - **Descripcion**: Wrapper unificado sobre la API de Polymarket. Encapsula tanto la Gamma API (datos publicos de mercados, sin autenticacion) como la CLOB API (trading, requiere firma). En esta fase solo se implementan los metodos de lectura; los de trading se stubbean.
  - **Archivo nuevo**: `backend/app/services/polymarket/connector.py`
  - **Clase**: `PolymarketConnector`
  - **Metodos a implementar**:
    - `__init__(self)` — Lee config de `Config`, inicializa HTTP session
    - `get_active_markets(self, limit=50, category=None, min_volume=0) -> List[Dict]` — Llama a `GET https://gamma-api.polymarket.com/markets` con filtros. Retorna lista de mercados con campos: `condition_id`, `question`, `outcomes`, `tokens`, `volume`, `end_date`, `active`, `closed`
    - `get_market_detail(self, condition_id: str) -> Dict` — Detalle de un mercado especifico incluyendo descripcion completa, reglas de resolucion, tokens
    - `get_market_price(self, token_id: str) -> Dict` — Precio mid-point del token (probabilidad implicita). Usa el endpoint CLOB `GET /midpoint?token_id=`
    - `get_orderbook(self, token_id: str) -> Dict` — Libro de ordenes completo (bids/asks). Usa `GET /book?token_id=`
    - `place_order(self, ...) -> Dict` — **STUB en esta fase**. Retorna `{"status": "stub", "message": "Trading not implemented yet"}`
  - **Patron a seguir**: Estructura similar a `backend/app/utils/llm_client.py` — constructor lee config, metodos son stateless, retries con backoff, logging con `get_logger()`
  - **Endpoints**:
    - Gamma API: `https://gamma-api.polymarket.com/` (sin auth, rate limit ~1000/hora)
    - CLOB API: `https://clob.polymarket.com/` (auth requerida para trading)
  - **Criterio de completado**: `connector.get_active_markets(limit=5)` retorna 5 mercados con precios reales

### 1.2 Pipeline de Ingestion de Noticias

- [ ] **T-007** — Crear `backend/app/services/polymarket/news_ingestor.py`
  - **Descripcion**: Motor de ingestion multi-fuente que recoge noticias y contexto relevante para un evento de Polymarket. Cada fuente es un metodo independiente con fallback gracioso si la API no esta disponible. El output es una lista de strings de texto plano, exactamente el formato que `OntologyGenerator.generate()` acepta como `document_texts`.
  - **Archivo nuevo**: `backend/app/services/polymarket/news_ingestor.py`
  - **Clase**: `NewsIngestor`
  - **Metodos a implementar**:
    - `__init__(self)` — Lee config (RSS feeds, API keys)
    - `fetch_rss(self, feed_urls: List[str], query: str, max_articles: int = 20) -> List[Dict]` — Parsea feeds RSS/Atom con `feedparser`. Filtra articulos por relevancia (query match en titulo/descripcion). Retorna `[{title, summary, link, published}]`
    - `fetch_newsapi(self, query: str, from_date: str = None, max_articles: int = 20) -> List[Dict]` — Llama a `GET https://newsapi.org/v2/everything?q={query}&apiKey={key}`. Free tier: 100 requests/dia, resultados de hace 1 mes. Skip si `NEWSAPI_KEY` no esta configurada
    - `fetch_web_search(self, query: str, max_results: int = 10) -> List[Dict]` — Busqueda web generica. Opciones de implementacion por orden de preferencia: (1) Tavily API si hay key, (2) DuckDuckGo scraping basico con `requests`, (3) Skip con warning
    - `fetch_twitter(self, query: str, max_tweets: int = 50) -> List[Dict]` — Tweets relevantes. Opciones: (1) Twitter API v2 si hay `TWITTER_BEARER_TOKEN`, (2) `snscrape` como fallback gratuito, (3) Skip con warning. Retorna `[{text, author, created_at, metrics}]`
    - `fetch_market_description(self, market: Dict) -> str` — Extrae la pregunta, descripcion y reglas de resolucion del propio mercado Polymarket como texto seed. Esto siempre funciona y garantiza al menos un documento de input
    - `fetch_all(self, market_question: str, market: Dict = None, max_total: int = 50) -> List[str]` — Ejecuta todas las fuentes disponibles en paralelo (con `concurrent.futures`), deduplica por hash SHA-256 del contenido, concatena titulo+contenido de cada articulo, y retorna lista de strings
    - `_deduplicate(self, articles: List[Dict]) -> List[Dict]` — Deduplicacion por hash de URL y similitud de contenido
  - **Almacenamiento**: Articulos crudos se guardan en `uploads/polymarket/news/<market_id>/` como archivos `.json` para debug y cache
  - **Patron a seguir**: Estructura similar a `backend/app/utils/file_parser.py` — metodos de extraccion independientes, manejo gracioso de errores
  - **Criterio de completado**: `ingestor.fetch_all("Will Bitcoin reach 100k by 2026?")` retorna al menos 5 documentos de texto (como minimo la descripcion del mercado + RSS si hay feeds configurados)

### 1.3 Ontologia de Dominio Financiero

- [ ] **T-008** — Crear `backend/app/services/polymarket/market_ontology.py`
  - **Descripcion**: System prompt para el `OntologyGenerator` adaptado al dominio de mercados de prediccion y eventos financieros/politicos. Reemplaza las entidades militares (MilitaryUnit, Threat, Route...) por entidades de mercado (Event, Catalyst, RiskFactor...). Sigue exactamente el mismo formato JSON que el prompt militar de `ontology_generator.py` lineas 12-156.
  - **Archivo nuevo**: `backend/app/services/polymarket/market_ontology.py`
  - **Constante**: `MARKET_ONTOLOGY_SYSTEM_PROMPT`
  - **Entity types (10, misma estructura que el militar)**:
    1. `Event` — El evento de prediccion principal (eleccion, lanzamiento, decision regulatoria)
    2. `Actor` — Persona o entidad con influencia sobre el outcome (politico, CEO, regulador)
    3. `DataSource` — Fuente de informacion que informa la prediccion (encuesta, informe, indice)
    4. `Catalyst` — Evento proximo que podria mover la probabilidad (discurso, votacion, earnings)
    5. `RiskFactor` — Amenaza o incertidumbre que afecta el outcome (regulacion, cisne negro)
    6. `MarketIndicator` — Senal cuantitativa (precio, volumen, on-chain metric, poll number)
    7. `TimelineMarker` — Hito temporal clave (deadline, fecha de resolucion, milestone)
    8. `Regulation` — Marco regulatorio relevante (ley, propuesta, orden ejecutiva)
    9. `Organization` — **Fallback** para instituciones no cubiertas (empresa, gobierno, ONG)
    10. `Person` — **Fallback** para individuos no cubiertos por Actor
  - **Edge types (8-10)**:
    - `INFLUENCES` — Actor/DataSource influye en Event/RiskFactor
    - `TRIGGERS` — Catalyst desencadena cambio en Event
    - `CONTRADICTS` — DataSource/Prediction contradice otro
    - `SUPPORTS_OUTCOME` — Evidencia que apoya un outcome especifico (YES/NO)
    - `REPORTED_BY` — Informacion reportada por DataSource
    - `CORRELATED_WITH` — Eventos/indicadores correlacionados
    - `PRECEDED_BY` — Secuencia temporal entre eventos
    - `MITIGATES` — Factor que reduce un RiskFactor
    - `REGULATES` — Regulation que afecta a Event/Actor/Organization
  - **Criterio de completado**: Se puede instanciar `OntologyGenerator(system_prompt=MARKET_ONTOLOGY_SYSTEM_PROMPT)` y generar una ontologia financiera valida con el formato JSON esperado

- [ ] **T-009** — Modificar `backend/app/services/ontology_generator.py` para aceptar prompt inyectable
  - **Descripcion**: Cambio minimo al `OntologyGenerator` existente para permitir inyectar un system prompt personalizado sin romper la funcionalidad actual. Actualmente el constructor (linea 166) no acepta prompt, y `generate()` (linea 193) usa la constante `ONTOLOGY_SYSTEM_PROMPT` directamente.
  - **Archivo a modificar**: `backend/app/services/ontology_generator.py` (existente)
  - **Cambio 1** — Constructor (linea 166-167):
    ```python
    # ANTES:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    # DESPUES:
    def __init__(self, llm_client: Optional[LLMClient] = None, system_prompt: Optional[str] = None):
        self.llm_client = llm_client or LLMClient()
        self.system_prompt = system_prompt or ONTOLOGY_SYSTEM_PROMPT
    ```
  - **Cambio 2** — Metodo `generate()` (linea 193):
    ```python
    # ANTES:
    {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},

    # DESPUES:
    {"role": "system", "content": self.system_prompt},
    ```
  - **Impacto**: 100% retrocompatible. Todos los usos existentes sin `system_prompt` siguen usando el prompt militar por defecto
  - **Criterio de completado**: Tests existentes pasan sin cambios + `OntologyGenerator(system_prompt="custom")` usa el prompt custom

### 1.4 Paper Trading Ledger

- [ ] **T-010** — Crear `backend/app/services/polymarket/paper_ledger.py`
  - **Descripcion**: Sistema de paper trading que registra trades simulados, rastrea un balance virtual, y calcula metricas de rendimiento. Persiste en un archivo JSON para sobrevivir reinicios del servidor. Sirve como herramienta de validacion antes de arriesgar dinero real.
  - **Archivo nuevo**: `backend/app/services/polymarket/paper_ledger.py`
  - **Dataclasses**:
    ```python
    @dataclass
    class PaperTrade:
        trade_id: str               # UUID unico
        market_id: str              # condition_id de Polymarket
        market_question: str        # Texto de la pregunta del mercado
        outcome: str                # "YES" o "NO"
        prob_estimate: float        # Probabilidad estimada por el sistema (0-1)
        market_price: float         # Precio de mercado al momento del trade (0-1)
        edge: float                 # prob_estimate - market_price
        kelly_fraction: float       # Fraccion Kelly calculada
        size_usd: float             # Tamano del trade en USD
        timestamp: str              # ISO 8601
        status: str                 # "open" | "won" | "lost" | "cancelled"
        resolved_at: Optional[str]  # Cuando se resolvio el mercado
        pnl: Optional[float]       # Profit/loss del trade

    @dataclass
    class PaperPortfolio:
        initial_balance: float      # Balance inicial (default $200)
        current_balance: float      # Balance actual
        trades: List[PaperTrade]    # Historial completo
        total_pnl: float            # P&L acumulado
        created_at: str             # Cuando se creo el portfolio
    ```
  - **Clase**: `PaperLedger`
  - **Metodos**:
    - `__init__(self, data_dir: str = None)` — Carga o crea portfolio desde JSON
    - `record_trade(self, trade: PaperTrade) -> str` — Registra nuevo trade, actualiza balance, persiste
    - `resolve_trade(self, trade_id: str, won: bool) -> PaperTrade` — Resuelve un trade abierto, calcula P&L
    - `get_open_trades(self) -> List[PaperTrade]` — Trades aun sin resolver
    - `get_summary(self) -> Dict` — Resumen: balance, trades totales, win rate, P&L, ROI
    - `calculate_brier_score(self) -> float` — Calibracion de probabilidades: `mean((prob - outcome)^2)` donde outcome es 0 o 1. Mas bajo = mejor calibrado. Solo trades resueltos
    - `calculate_roi(self) -> float` — Return on investment: `total_pnl / initial_balance`
    - `_save(self)` / `_load(self)` — Persistencia JSON en `uploads/polymarket/paper_ledger.json`
  - **Patron a seguir**: `backend/app/models/project.py` (ProjectManager) — JSON persistence, singleton pattern
  - **Criterio de completado**: Se puede crear un trade, resolverlo, y verificar que el balance se actualiza correctamente. Brier score calcula para trades resueltos.

---

## FASE 2 — Simulacion de Enjambre + Extraccion de Probabilidad

> **Objetivo**: Ejecutar simulaciones de agentes por evento de mercado donde los agentes (derivados del grafo de conocimiento) debaten y opinan sobre el outcome probable. Extraer de la simulacion una probabilidad estructurada con nivel de confianza. Implementar Kelly Criterion para sizing de posiciones.
>
> **Prerequisito**: Fase 1 completada (grafos de conocimiento financiero construidos)
>
> **Entregable**: `ProbabilityEngine.full_analysis(market_id)` retorna un `MarketEstimate` con probabilidad, confianza y evidencia. `PositionSizer` calcula tamano optimo de trade.

### 2.1 Motor de Probabilidad

- [ ] **T-011** — Crear `backend/app/services/polymarket/probability_engine.py` — Scaffolding y `prepare_market_analysis()`
  - **Descripcion**: Primera parte del nucleo del sistema. Este metodo orquesta la fase de preparacion: obtiene datos del mercado, recoge noticias, genera ontologia financiera, y construye el grafo Zep. Reutiliza servicios MiroFish existentes sin modificarlos.
  - **Archivo nuevo**: `backend/app/services/polymarket/probability_engine.py`
  - **Clase**: `ProbabilityEngine`
  - **Metodo**: `prepare_market_analysis(self, market_id: str) -> Dict`
  - **Flujo interno**:
    1. `PolymarketConnector().get_market_detail(market_id)` → info del mercado
    2. `NewsIngestor().fetch_all(market['question'], market)` → lista de documentos
    3. `OntologyGenerator(system_prompt=MARKET_ONTOLOGY_SYSTEM_PROMPT).generate(docs, market['question'])` → ontologia
    4. `GraphBuilderService().create_graph()` → crea grafo Zep
    5. `GraphBuilderService().set_ontology(graph_id, ontology)` → aplica ontologia
    6. `GraphBuilderService().add_text_batches(graph_id, docs)` → pobla el grafo
    7. Retorna `{"graph_id": str, "market": Dict, "ontology": Dict, "doc_count": int}`
  - **Servicios MiroFish reutilizados** (sin cambios):
    - `backend/app/services/ontology_generator.py` — Con `system_prompt` inyectado (T-009)
    - `backend/app/services/graph_builder.py` — Intacto
    - `backend/app/services/text_processor.py` — Intacto
  - **Criterio de completado**: `engine.prepare_market_analysis("some_market_id")` construye un grafo Zep con entidades financieras

- [ ] **T-012** — Implementar `configure_market_agents()` en `probability_engine.py`
  - **Descripcion**: Genera perfiles de agentes a partir de las entidades del grafo financiero. Cada entidad del grafo se convierte en un agente con una persona, stance (bullish/bearish/neutral), y nivel de influencia. Se asegura de incluir agentes contrarian para calibracion.
  - **Metodo**: `configure_market_agents(self, graph_id: str, market: Dict) -> List[Dict]`
  - **Flujo interno**:
    1. `ZepEntityReader().get_entities(graph_id)` → entidades del grafo
    2. Para cada entidad, mapear entity type a rol de mercado:
       - `Actor` → analista politico/economico (stance variable segun contexto)
       - `DataSource` → periodista de datos (stance neutral, alta influencia)
       - `RiskFactor` → analista de riesgo (stance bearish, alta influencia)
       - `Catalyst` → event trader (stance variable, alta actividad)
       - `MarketIndicator` → quant analyst (stance basado en data, influencia media)
       - `Regulation` → regulatory analyst (stance cauteloso)
       - `Organization`/`Person` → general market participant
    3. Asignar contrarians: 20-30% de agentes con stance opuesto al consenso
    4. Usar `OasisProfileGenerator` para enriquecer personas con LLM
    5. Configurar `AgentActivityConfig` por agente con `sentiment_bias`, `stance`, `influence_weight`
  - **Servicios MiroFish reutilizados**:
    - `backend/app/services/zep_entity_reader.py` — Intacto
    - `backend/app/services/oasis_profile_generator.py` — Intacto
    - `backend/app/services/simulation_config_generator.py` — Referencia para `AgentActivityConfig`
  - **Criterio de completado**: Genera perfiles de agentes con stances variados (al menos 20% contrarian) y influence_weights diferenciados por rol

- [ ] **T-013** — Implementar `run_market_simulation()` en `probability_engine.py`
  - **Descripcion**: Ejecuta una simulacion OASIS corta (3-5 rondas) donde los agentes debaten sobre el outcome del evento en redes sociales simuladas (Twitter/Reddit). La simulacion es mas corta que la estandar de MiroFish porque solo necesitamos formacion de opinion, no viralidad.
  - **Metodo**: `run_market_simulation(self, graph_id: str, market: Dict, profiles: List[Dict], max_rounds: int = 5) -> str`
  - **Flujo interno**:
    1. Preparar configuracion de simulacion (tiempo simulado: 6-12 horas)
    2. Crear `SimulationRunner` con los perfiles generados
    3. Lanzar simulacion en background thread
    4. Retornar `simulation_id` para polling
  - **Servicio MiroFish reutilizado**: `backend/app/services/simulation_runner.py` — Intacto
  - **Diferencias vs simulacion estandar**: Menos rondas (3-5 vs 10+), tiempo simulado mas corto, sin necesidad de graph memory update (se puede omitir para velocidad)
  - **Criterio de completado**: Simulacion ejecuta 3-5 rondas con agentes actuando en plataformas simuladas

- [ ] **T-014** — Implementar `extract_probabilities()` en `probability_engine.py`
  - **Descripcion**: **Metodo central del sistema**. Extrae una probabilidad estructurada de la simulacion completada usando 4 capas de analisis progresivo.
  - **Metodo**: `extract_probabilities(self, simulation_id: str, graph_id: str, market: Dict) -> MarketEstimate`
  - **Dataclass de retorno**:
    ```python
    @dataclass
    class MarketEstimate:
        market_id: str
        market_question: str
        yes_probability: float      # 0.0 - 1.0
        confidence: float           # 0.0 - 1.0 (que tan seguro esta el sistema)
        agent_agreement: float      # 0.0 - 1.0 (proporcion de agentes alineados)
        evidence_for: List[str]     # Argumentos a favor del YES
        evidence_against: List[str] # Argumentos a favor del NO
        reasoning: str              # Resumen narrativo del LLM final
        agent_votes: Dict           # {agent_id: {probability, stance, influence}}
        timestamp: str
    ```
  - **Capas de extraccion**:
    1. **Interview Voting** — Usa el mecanismo de interview batch existente (`/api/simulation/interview/batch`) para preguntar a cada agente: *"Que probabilidad (0-100%) asignas a que {outcome}? Responde SOLO con un numero seguido de una frase de justificacion."* Parsea la respuesta numerica con regex
    2. **Weighted Aggregation** — `yes_prob = sum(agent_prob_i * influence_weight_i) / sum(influence_weight_i)`. Confidence = 1 - stddev de las probabilidades individuales (alta varianza = baja confianza). Agreement = proporcion de agentes cuya probabilidad esta dentro de +/-15% del promedio
    3. **InsightForge Synthesis** — `ZepToolsService().insight_forge(graph_id, "What evidence supports/opposes {outcome}?")`. Extrae hechos pro y contra del grafo para dar fundamento a la probabilidad
    4. **LLM Final Calibration** — Un LLM recibe: probabilidad agregada, votos individuales, evidencia pro/contra, y el contexto del mercado. Le pide una probabilidad final calibrada con razonamiento. Esto corrige sesgos sistematicos del enjambre
  - **Servicios MiroFish reutilizados**:
    - `backend/app/services/zep_tools.py` — `InsightForge` (linea 945+)
    - Interview batch via API endpoints existentes
  - **Criterio de completado**: Retorna `MarketEstimate` con `yes_probability` entre 0-1, confidence > 0, y listas de evidencia no vacias

- [ ] **T-015** — Implementar `full_analysis()` en `probability_engine.py`
  - **Descripcion**: Pipeline end-to-end que encadena prepare → configure → simulate → extract. Gestiona el flujo asincrono y reporta progreso.
  - **Metodo**: `full_analysis(self, market_id: str, callback: Callable = None) -> MarketEstimate`
  - **Flujo**: Llama secuencialmente a T-011, T-012, T-013, T-014. Usa `TaskManager` existente para tracking de progreso.
  - **Criterio de completado**: `engine.full_analysis("market_id")` retorna un `MarketEstimate` completo

### 2.2 Position Sizing

- [ ] **T-016** — Crear `backend/app/services/polymarket/position_sizer.py`
  - **Descripcion**: Modulo de Kelly Criterion adaptado a mercados binarios de prediccion. Calcula el tamano optimo de apuesta dado una probabilidad estimada y un precio de mercado. Incluye multiples capas de seguridad.
  - **Archivo nuevo**: `backend/app/services/polymarket/position_sizer.py`
  - **Clase**: `PositionSizer`
  - **Metodos**:
    - `kelly_fraction(self, estimated_prob: float, market_price: float) -> float`
      - Para mercado binario: `b = (1/market_price) - 1` (odds implicitas del mercado)
      - Kelly: `f* = (b * p - (1-p)) / b` donde `p = estimated_prob`
      - Si `f* < 0`, retorna 0 (no hay edge)
      - Si `estimated_prob <= market_price`, retorna 0 (no apostar contra el mercado sin edge)
    - `fractional_kelly(self, estimated_prob: float, market_price: float, fraction: float = 0.25) -> float`
      - Retorna `kelly_fraction() * fraction`
      - Default 25% (quarter Kelly) — conservador, protege contra errores de estimacion
    - `calculate_position(self, estimate: MarketEstimate, bankroll: float) -> TradeDecision`
      - **Dataclass TradeDecision**:
        ```python
        @dataclass
        class TradeDecision:
            should_trade: bool
            side: str              # "YES" o "NO"
            size_usd: float        # Tamano en USD
            kelly_fraction: float
            edge: float            # Diferencia prob estimada vs mercado
            risk_checks: Dict      # {check_name: passed}
            rejection_reason: str  # Si should_trade=False, por que
        ```
      - **Risk checks** (TODOS deben pasar para `should_trade=True`):
        1. `edge >= Config.POLYMARKET_MIN_EDGE` (default 10%) — Edge insuficiente
        2. `size_usd <= Config.POLYMARKET_MAX_TRADE_USD` (default $10) — Cap por trade
        3. `size_usd <= bankroll * 0.05` — Nunca mas del 5% del bankroll en un trade
        4. `estimate.confidence >= 0.5` — Confianza minima del sistema
        5. `estimate.agent_agreement >= 0.6` — Al menos 60% de agentes alineados
        6. `kelly_fraction > 0.01` — Kelly debe ser positivo y significativo
      - Si algun check falla, `should_trade=False` con `rejection_reason` explicando por que
  - **Criterio de completado**: `sizer.calculate_position(estimate, bankroll=200)` retorna decision correcta. Con edge 15% y confianza 0.8 → `should_trade=True`. Con edge 5% → `should_trade=False`

---

## FASE 3 — Trading Engine + API Endpoints + Automatizacion

> **Objetivo**: Crear el orquestador que ejecuta el ciclo completo (scan → analyze → size → trade), los endpoints REST para el frontend, y un script de automatizacion que puede correr como cron job.
>
> **Prerequisito**: Fase 2 completada (probabilidades y position sizing funcionan)
>
> **Entregable**: Bot ejecutable via CLI que hace paper trading automatico. API REST completa para el frontend.

### 3.1 Trading Engine

- [ ] **T-017** — Crear `backend/app/services/polymarket/trading_engine.py`
  - **Descripcion**: Orquestador principal del bot. Coordina el escaneo de mercados, analisis con el enjambre, decision de trading, y ejecucion (paper o live). Incluye safety mechanisms: kill switch, rate limiting, logging.
  - **Archivo nuevo**: `backend/app/services/polymarket/trading_engine.py`
  - **Clase**: `TradingEngine`
  - **Metodos**:
    - `__init__(self)` — Inicializa connector, engine, sizer, ledger
    - `scan_markets(self, limit: int = 20) -> List[Dict]` — Filtra mercados interesantes:
      - Activos y no cerrados
      - Volumen diario > $1000 (evitar mercados muertos)
      - Resolucion en los proximos 7-90 dias (ni demasiado cerca ni demasiado lejos)
      - Sin posicion abierta en ese mercado (evitar duplicados)
      - Precio entre 0.10 y 0.90 (evitar extremos sin edge)
    - `analyze_market(self, market_id: str) -> MarketEstimate` — Llama a `ProbabilityEngine.full_analysis()`
    - `evaluate_trade(self, estimate: MarketEstimate) -> TradeDecision` — Llama a `PositionSizer.calculate_position()`
    - `execute_trade(self, market_id: str, decision: TradeDecision) -> Dict` — Si `Config.POLYMARKET_MODE == 'paper'`: registra en `PaperLedger`. Si `'live'`: llama a `PolymarketConnector.place_order()`. Siempre loguea
    - `run_cycle(self) -> Dict` — Un ciclo completo:
      1. Check kill switch (`uploads/polymarket/KILL_SWITCH` existe → abort)
      2. Check rate limits (max 5 trades/dia, max 1/mercado/6h)
      3. `scan_markets()` → top N mercados
      4. Para cada mercado: `analyze_market()` → `evaluate_trade()` → `execute_trade()` si procede
      5. Retorna resumen del ciclo
    - `is_kill_switch_active(self) -> bool` — Verifica existencia del archivo
    - `_check_rate_limits(self, market_id: str) -> bool` — Verifica limites
  - **Logging**: Todo a `uploads/polymarket/bot_log.jsonl` (una linea JSON por evento)
  - **Criterio de completado**: `engine.run_cycle()` escanea mercados, analiza al menos 1, y registra decision en log

### 3.2 Completar Connector con Trading Real

- [ ] **T-018** — Actualizar `connector.py` con metodos de trading via `py-clob-client`
  - **Descripcion**: Implementar los metodos de trading que estaban stubbeados en T-006. Usa el SDK oficial `py-clob-client` para firmar y enviar ordenes al CLOB de Polymarket. TODAS las operaciones de trading verifican `POLYMARKET_MODE` antes de ejecutar.
  - **Archivo a modificar**: `backend/app/services/polymarket/connector.py`
  - **Metodos nuevos**:
    - `_init_clob_client(self) -> ClobClient` — Inicializa `py-clob-client` con private key y chain_id=137 (Polygon). Solo se ejecuta si `POLYMARKET_MODE == 'live'`
    - `authenticate(self) -> Dict` — L1 auth: firma EIP-712. Deriva API credentials (L2)
    - `place_limit_order(self, token_id: str, side: str, size: float, price: float) -> Dict` — Crea y envia orden limite. Verifica modo antes de ejecutar. En paper mode: retorna mock
    - `get_positions(self) -> List[Dict]` — Posiciones abiertas actuales
    - `cancel_order(self, order_id: str) -> Dict` — Cancela orden activa
    - `get_trades_history(self) -> List[Dict]` — Historial de trades ejecutados
  - **Safety**: Cada metodo de escritura hace `if Config.POLYMARKET_MODE != 'live': return {"error": "Not in live mode"}`
  - **Dependencia**: `py-clob-client` (anadido en T-004)
  - **Criterio de completado**: En modo paper, metodos retornan mock. En modo live (con credentials validos), puede colocar una orden real

### 3.3 API REST (Blueprint Flask)

- [ ] **T-019** — Crear `backend/app/api/polymarket.py` (blueprint Flask)
  - **Descripcion**: Blueprint Flask con todos los endpoints REST necesarios para el frontend y para control externo del bot. Sigue exactamente el patron de `backend/app/api/graph.py` y `backend/app/api/simulation.py`.
  - **Archivo nuevo**: `backend/app/api/polymarket.py`
  - **Endpoints**:
    ```
    GET  /api/polymarket/markets                    → Mercados activos con precios
    GET  /api/polymarket/markets/<id>               → Detalle de mercado
    POST /api/polymarket/analyze/<market_id>        → Lanza analisis completo (async, retorna task_id)
    GET  /api/polymarket/analysis/<task_id>         → Progreso del analisis (polling)
    GET  /api/polymarket/analysis/<market_id>/result → Resultado final con MarketEstimate
    POST /api/polymarket/trade                      → Ejecutar trade manual (paper o live)
    GET  /api/polymarket/portfolio                  → Estado del paper portfolio
    GET  /api/polymarket/portfolio/trades            → Historial de trades
    GET  /api/polymarket/dashboard                  → Resumen: P&L, Brier, win rate, ROI
    POST /api/polymarket/kill-switch                → Activar/desactivar kill switch
    POST /api/polymarket/bot/start                  → Iniciar bot loop (background thread)
    POST /api/polymarket/bot/stop                   → Detener bot loop
    GET  /api/polymarket/bot/status                 → Estado del bot (running, idle, last_cycle)
    GET  /api/polymarket/bot/logs                   → Ultimas N entradas del log
    ```
  - **Patron**: Cada endpoint wrappea try/except, retorna `{"success": bool, "data": ...}` o `{"success": false, "error": ...}`
  - **Async**: Analisis y bot loop usan `threading.Thread` + `TaskManager` (mismo patron que graph building)
  - **Criterio de completado**: `curl http://localhost:5001/api/polymarket/markets` retorna JSON con mercados

- [ ] **T-020** — Registrar blueprint `polymarket_bp` en la app Flask
  - **Descripcion**: Anadir el blueprint al `__init__.py` del modulo API y registrarlo en la app factory.
  - **Archivos a modificar**:
    - `backend/app/api/__init__.py` (linea 7-13): Anadir `polymarket_bp = Blueprint('polymarket', __name__)` y `from . import polymarket`
    - `backend/app/__init__.py` (linea 66-69): Anadir `from .api import polymarket_bp` y `app.register_blueprint(polymarket_bp, url_prefix='/api/polymarket')`
  - **Criterio de completado**: El servidor Flask arranca sin errores y responde en `/api/polymarket/`

### 3.4 Script de Automatizacion

- [ ] **T-021** — Crear `backend/scripts/run_polymarket_bot.py`
  - **Descripcion**: Script standalone ejecutable desde terminal que lanza el bot. Soporta modo single-run (`--once`) y loop continuo (`--loop` con intervalo configurable). Maneja signals para shutdown graceful.
  - **Archivo nuevo**: `backend/scripts/run_polymarket_bot.py`
  - **CLI args**:
    - `--mode paper|live` — Override del modo (default: lee de Config)
    - `--once` — Ejecuta un solo ciclo y sale
    - `--loop` — Ejecuta ciclos continuos
    - `--interval 1800` — Segundos entre ciclos en modo loop (default 30 min)
    - `--max-markets 3` — Maximo de mercados a analizar por ciclo
  - **Comportamiento**:
    - Setup logging a stdout + `uploads/polymarket/bot_log.jsonl`
    - Registra signal handlers (SIGINT, SIGTERM) para shutdown graceful
    - En modo loop: ejecuta `TradingEngine.run_cycle()` cada N segundos
    - Al terminar: imprime resumen del session (trades realizados, P&L parcial)
  - **Patron a seguir**: `backend/scripts/run_parallel_simulation.py`
  - **Criterio de completado**: `python backend/scripts/run_polymarket_bot.py --mode paper --once` ejecuta un ciclo completo y sale

---

## FASE 4 — Frontend Vue: Dashboard Polymarket

> **Objetivo**: Interfaz visual integrada en el frontend Vue existente de MiroFish para navegar mercados, lanzar analisis, ver resultados de simulacion, gestionar portfolio y controlar el bot.
>
> **Prerequisito**: Fase 3 completada (API endpoints funcionan)
>
> **Entregable**: Ruta `/polymarket` en la app Vue con 4 tabs funcionales

### 4.1 API Client

- [ ] **T-022** — Crear `frontend/src/api/polymarket.js`
  - **Descripcion**: Modulo de funciones API que wrappea todas las llamadas al backend Polymarket. Sigue el patron exacto de `frontend/src/api/graph.js` y `frontend/src/api/simulation.js`.
  - **Archivo nuevo**: `frontend/src/api/polymarket.js`
  - **Funciones a exportar**:
    ```javascript
    // Mercados
    export function getMarkets(params)                    // GET /api/polymarket/markets
    export function getMarketDetail(marketId)             // GET /api/polymarket/markets/:id

    // Analisis
    export function analyzeMarket(marketId)               // POST /api/polymarket/analyze/:id
    export function getAnalysisStatus(taskId)             // GET /api/polymarket/analysis/:taskId
    export function getAnalysisResult(marketId)           // GET /api/polymarket/analysis/:id/result

    // Trading
    export function executeTrade(data)                    // POST /api/polymarket/trade

    // Portfolio
    export function getPortfolio()                        // GET /api/polymarket/portfolio
    export function getPortfolioTrades()                  // GET /api/polymarket/portfolio/trades
    export function getDashboard()                        // GET /api/polymarket/dashboard

    // Bot Control
    export function toggleKillSwitch(active)              // POST /api/polymarket/kill-switch
    export function startBot(config)                      // POST /api/polymarket/bot/start
    export function stopBot()                             // POST /api/polymarket/bot/stop
    export function getBotStatus()                        // GET /api/polymarket/bot/status
    export function getBotLogs(limit)                     // GET /api/polymarket/bot/logs
    ```
  - **Usa**: `requestWithRetry` de `frontend/src/api/index.js` para las llamadas criticas
  - **Criterio de completado**: Todas las funciones exportan correctamente y hacen calls al backend

### 4.2 Ruta y Vista Principal

- [ ] **T-023** — Anadir ruta `/polymarket` a `frontend/src/router/index.js`
  - **Descripcion**: Nueva ruta en el router de Vue que carga la vista Polymarket. Props: ninguna (la vista gestiona su propio estado).
  - **Archivo a modificar**: `frontend/src/router/index.js` (existente, 52 lineas)
  - **Cambio**: Importar `PolymarketView` y anadir ruta
  - **Criterio de completado**: Navegar a `http://localhost:3000/polymarket` carga la vista

- [ ] **T-024** — Crear `frontend/src/views/PolymarketView.vue`
  - **Descripcion**: Vista principal del dashboard Polymarket. Layout split como el resto de MiroFish (GraphPanel a la izquierda, workbench a la derecha). El workbench tiene 4 tabs: Markets, Analysis, Portfolio, Bot Control.
  - **Archivo nuevo**: `frontend/src/views/PolymarketView.vue`
  - **Layout**:
    - Header con titulo "Polymarket Swarm Intelligence" y toggle de vista (graph/split/workbench)
    - Panel izquierdo: `GraphPanel.vue` reutilizado (muestra el grafo del mercado analizado)
    - Panel derecho: Tabs con los 4 componentes
  - **Estado reactivo**: `currentTab`, `selectedMarket`, `currentAnalysis`, `graphData`
  - **Criterio de completado**: La vista renderiza con 4 tabs navegables

### 4.3 Componentes del Dashboard

- [ ] **T-025** — Crear `frontend/src/components/polymarket/MarketScanner.vue`
  - **Descripcion**: Tabla de mercados activos de Polymarket con filtros, precios en tiempo real, e indicadores de edge cuando hay analisis disponible. Boton "Analizar" lanza el pipeline completo.
  - **Archivo nuevo**: `frontend/src/components/polymarket/MarketScanner.vue`
  - **Features UI**:
    - Tabla con columnas: Mercado (pregunta), Precio YES, Precio NO, Volumen 24h, Fecha resolucion, Edge (si hay analisis), Acciones
    - Filtros: categoria dropdown, volumen minimo, rango de precio
    - Boton "Analizar" por fila → llama `analyzeMarket()`, muestra spinner durante analisis
    - Indicador de color por edge: verde (>15%), amarillo (10-15%), gris (sin analisis)
    - Paginacion (20 mercados por pagina)
    - Auto-refresh cada 60 segundos
  - **Criterio de completado**: Muestra mercados reales de Polymarket con precios actualizados

- [ ] **T-026** — Crear `frontend/src/components/polymarket/MarketAnalysis.vue`
  - **Descripcion**: Visualizacion detallada del resultado de un analisis de enjambre. Muestra la probabilidad estimada vs precio de mercado, la distribucion de opiniones de agentes, evidencia pro/contra, y la recomendacion de trading.
  - **Archivo nuevo**: `frontend/src/components/polymarket/MarketAnalysis.vue`
  - **Features UI**:
    - **Header**: Pregunta del mercado + badges (confidence, agreement)
    - **Gauge chart** (D3): Probabilidad estimada vs precio de mercado, con zona de edge coloreada
    - **Distribucion de agentes**: Histograma de votos de agentes (D3 bar chart) mostrando distribucion de probabilidades individuales
    - **Evidencia**: Dos columnas "A favor" / "En contra" con bullet points del InsightForge
    - **Recomendacion**: Card grande con: BUY YES / BUY NO / NO TRADE + tamano Kelly recomendado + reasoning del LLM
    - **Boton "Ejecutar Trade"**: Solo aparece si `should_trade=true`. Pide confirmacion antes de ejecutar
  - **Criterio de completado**: Muestra analisis completo con gauge, histograma y recomendacion

- [ ] **T-027** — Crear `frontend/src/components/polymarket/Portfolio.vue`
  - **Descripcion**: Dashboard de portfolio con balance, posiciones abiertas, historial de trades, grafico P&L, y metricas de calibracion.
  - **Archivo nuevo**: `frontend/src/components/polymarket/Portfolio.vue`
  - **Features UI**:
    - **Cards top**: Balance actual, P&L total, ROI %, Win rate, Brier Score
    - **Posiciones abiertas**: Tabla con mercado, lado, tamano, precio entrada, precio actual, P&L no realizado
    - **Historial**: Tabla scrollable con todos los trades (con filtro por estado: open/won/lost)
    - **Grafico P&L** (D3): Linea temporal de balance acumulado
    - **Calibracion** (D3, opcional): Scatter plot de probabilidad estimada vs outcome real
  - **Criterio de completado**: Muestra portfolio con metricas y grafico P&L

- [ ] **T-028** — Crear `frontend/src/components/polymarket/BotControl.vue`
  - **Descripcion**: Panel de control del bot automatizado. Permite arrancar/parar el bot, configurar parametros, ver estado en tiempo real, y activar el kill switch.
  - **Archivo nuevo**: `frontend/src/components/polymarket/BotControl.vue`
  - **Features UI**:
    - **Estado**: Indicador grande (Running / Stopped / Error) con timestamp del ultimo ciclo
    - **Controles**: Boton Start/Stop, toggle Paper/Live (con confirmacion para Live), Kill Switch (boton rojo grande)
    - **Configuracion**: Sliders/inputs para: max trade USD, min edge %, Kelly fraction, max mercados/ciclo, intervalo entre ciclos
    - **Logs en vivo**: Area de texto scrollable mostrando las ultimas 50 entradas del log del bot, con auto-refresh cada 5 segundos
    - **Estadisticas de session**: Ciclos ejecutados, mercados analizados, trades colocados, P&L de session
  - **Criterio de completado**: Se puede arrancar/parar el bot desde la UI y ver logs en tiempo real

### 4.4 Navegacion

- [ ] **T-029** — Anadir link a Polymarket en la navegacion principal (Home.vue o header)
  - **Descripcion**: Anadir un enlace/boton en la home page o header de MiroFish que lleve a `/polymarket`. Debe integrarse visualmente con el diseno existente.
  - **Archivo a modificar**: `frontend/src/views/Home.vue` o componente de navegacion global
  - **Criterio de completado**: Desde la home page se puede navegar a `/polymarket` con un click

---

## FASE 5 — Testing, Calibracion y Refinamiento

> **Objetivo**: Validar que el sistema funciona end-to-end, medir calibracion de probabilidades, y refinar antes de arriesgar dinero real.
>
> **Prerequisito**: Fases 0-4 completadas
>
> **Entregable**: Bot probado con paper trading durante 2+ semanas, Brier score medido, decisiones documentadas

### 5.1 Testing

- [ ] **T-030** — Tests unitarios para `position_sizer.py`
  - **Descripcion**: Tests que verifican la logica de Kelly Criterion y los risk checks. Casos edge: edge negativo, probabilidad en extremos (0, 1), bankroll cero.
  - **Archivo nuevo**: `backend/tests/test_position_sizer.py`
  - **Casos de test**:
    - Kelly con edge positivo → fraccion > 0
    - Kelly con edge negativo → fraccion = 0
    - Fractional Kelly = 25% del full Kelly
    - Risk check: edge < min → should_trade = False
    - Risk check: size > max → capeado al max
    - Risk check: confianza < 0.5 → should_trade = False
    - Risk check: agreement < 0.6 → should_trade = False
  - **Criterio de completado**: Todos los tests pasan

- [ ] **T-031** — Tests unitarios para `paper_ledger.py`
  - **Descripcion**: Tests de creacion de trades, resolucion, calculo de Brier score, persistencia JSON.
  - **Archivo nuevo**: `backend/tests/test_paper_ledger.py`
  - **Criterio de completado**: Todos los tests pasan

- [ ] **T-032** — Tests de integracion para `connector.py`
  - **Descripcion**: Tests que verifican la conexion real a Gamma API (datos publicos, no requiere auth). Mock para metodos de trading.
  - **Archivo nuevo**: `backend/tests/test_connector.py`
  - **Criterio de completado**: `get_active_markets()` retorna datos reales de Polymarket

- [ ] **T-033** — Tests de integracion para `news_ingestor.py`
  - **Descripcion**: Tests que verifican cada fuente de noticias individualmente y el `fetch_all` combinado. Las fuentes no disponibles deben fallar graciosamente.
  - **Archivo nuevo**: `backend/tests/test_news_ingestor.py`
  - **Criterio de completado**: `fetch_all()` retorna al menos 1 documento (market description) aunque las APIs externas fallen

- [ ] **T-034** — Test end-to-end del pipeline completo
  - **Descripcion**: Test que ejecuta el pipeline completo desde un market_id real: news → ontology → graph → simulation → probability → position sizing → paper trade. Puede tardar 10-30 minutos.
  - **Archivo nuevo**: `backend/tests/test_e2e_polymarket.py`
  - **Criterio de completado**: El pipeline completo ejecuta sin errores y produce un trade paper

### 5.2 Calibracion

- [ ] **T-035** — Ejecutar paper trading durante 2+ semanas
  - **Descripcion**: Correr el bot en modo paper con mercados reales. Registrar todas las estimaciones y esperar a que los mercados se resuelvan para medir calibracion.
  - **Proceso**:
    1. Configurar bot con `--mode paper --loop --interval 3600` (cada hora)
    2. Dejar correr durante 2-4 semanas
    3. A medida que mercados se resuelvan, llamar `resolve_trade()` manualmente o automatizar
    4. Calcular Brier score con muestra suficiente (min 20 trades resueltos)
  - **Objetivo**: Brier score < 0.25 (mejor que azar). Si es > 0.30, hay que investigar y recalibrar
  - **Criterio de completado**: 20+ trades resueltos con Brier score calculado

- [ ] **T-036** — Analizar resultados y ajustar parametros
  - **Descripcion**: Basado en los resultados de paper trading, ajustar: min_edge, Kelly fraction, numero de rondas de simulacion, pesos de influencia, threshold de confianza.
  - **Criterio de completado**: Parametros optimizados documentados en `.env`

### 5.3 Opcional: Mejoras

- [ ] **T-037** — Multi-model ensemble para estimaciones
  - **Descripcion**: Correr la estimacion final con multiples LLMs (ej: GPT-4o-mini + Claude + Qwen) y promediar. Trivial dado que `LLMClient` acepta `base_url` y `model` configurables.
  - **Archivo a modificar**: `probability_engine.py` — anadir metodo `_multi_model_estimate()`
  - **Criterio de completado**: Probabilidad final es promedio de 2+ modelos

- [ ] **T-038** — Cache de grafos para mercados estables
  - **Descripcion**: Si un mercado ya tiene un grafo construido y las noticias no han cambiado significativamente, reutilizar el grafo existente en vez de reconstruirlo. Ahorra 5-10 minutos por analisis.
  - **Archivo a modificar**: `probability_engine.py` — check cache antes de `prepare_market_analysis()`
  - **Criterio de completado**: Segundo analisis del mismo mercado es significativamente mas rapido

- [ ] **T-039** — Resolucion automatica de trades via Polymarket API
  - **Descripcion**: Polling periodico de mercados con trades abiertos. Si el mercado se resolvio, actualizar automaticamente el paper ledger.
  - **Archivo a modificar**: `trading_engine.py` — anadir metodo `check_resolutions()`
  - **Criterio de completado**: Trades se marcan como won/lost automaticamente cuando el mercado se resuelve

- [ ] **T-040** — Notificaciones Telegram
  - **Descripcion**: Enviar notificaciones via Telegram bot cuando: se detecta edge significativo, se ejecuta un trade, un mercado se resuelve, hay error critico.
  - **Archivo nuevo**: `backend/app/services/polymarket/notifications.py`
  - **Criterio de completado**: Recibe mensaje Telegram cuando el bot ejecuta un trade paper

### 5.4 Estrategias Avanzadas de Quant Trading

> Las siguientes dos tareas elevan el sistema de "bot que estima probabilidades" a "sistema cuantitativo completo". Implementan las dos piezas que faltan respecto a los bots profesionales de Polymarket: arbitraje estadístico entre mercados correlacionados (KL-Divergence) y actualización incremental de creencias (Bayes continuo). Ambas son independientes entre sí y pueden implementarse en cualquier orden.

- [ ] **T-041** — Scanner de Arbitraje por KL-Divergence entre Mercados Correlacionados
  - **Descripcion**: Sistema que detecta inconsistencias de precios entre mercados de Polymarket que deberían estar lógicamente relacionados. Esto es **arbitraje estadístico puro** — no necesita que tu modelo de probabilidad sea bueno, solo que **dos mercados sean inconsistentes entre sí**. Es la estrategia de menor riesgo y posiblemente la más rentable.
  - **Archivo nuevo**: `backend/app/services/polymarket/kl_scanner.py`

  - **Concepto matemático**:

    La divergencia KL mide cuánto difiere una distribución de probabilidad P de otra distribución Q:

    ```
    D_KL(P ‖ Q) = Σ Pᵢ · ln(Pᵢ / Qᵢ)
    ```

    Si dos mercados tratan sobre eventos relacionados (ej: "X gana la nominación" y "X gana la elección general"), sus distribuciones de probabilidad deberían ser **coherentes**. Si X tiene 70% de ganar la nominación, no puede tener 55% de ganar la general SIN una razón clara — porque ganar la general **requiere** ganar la nominación primero. La probabilidad coherente sería ~62% (P(general) = P(nominación) × P(general|nominación)).

    Cuando la KL-divergence entre dos mercados relacionados supera un threshold, hay una **oportunidad de arbitraje**: compras el infravalorado, vendes el sobrevalorado, y capturas la convergencia cuando el mercado se corrige.

  - **Clase**: `KLDivergenceScanner`
  - **Metodos a implementar**:

    - `__init__(self, connector: PolymarketConnector)` — Inicializa con el connector existente

    - `discover_related_markets(self, markets: List[Dict]) -> List[Tuple[Dict, Dict, str]]` — **Descubrimiento automático de pares correlacionados**. Este es el método más complejo. Estrategias:
      1. **Coincidencia de entidades**: Usa LLM para extraer la entidad principal de cada mercado ("Trump", "Bitcoin", "Fed"). Mercados con la misma entidad son candidatos a par
      2. **Relación lógica**: Identifica pares donde un outcome **implica** el otro (ej: "X gana primaria" → prerequisito de "X gana general")
      3. **Categoría Polymarket**: Mercados en la misma categoría (Politics, Crypto, Sports) con la misma entidad
      4. **Temporal**: Mercados sobre el mismo evento pero con diferentes fechas ("BTC > 100k en Q3" vs "BTC > 100k en Q4")
      - Retorna: lista de `(market_A, market_B, relationship_type)` donde `relationship_type` es "prerequisite", "correlated", "temporal_sequence", "same_entity"

    - `calculate_kl_divergence(self, p: List[float], q: List[float]) -> float` — KL-divergence entre dos distribuciones. Para mercados binarios: `P = [price_yes, price_no]`, `Q = [price_yes, price_no]`. Aplica smoothing Laplace (epsilon=0.001) para evitar log(0)
      ```python
      def calculate_kl_divergence(self, p: List[float], q: List[float]) -> float:
          eps = 0.001
          p = np.array(p) + eps
          q = np.array(q) + eps
          p = p / p.sum()  # renormalize
          q = q / q.sum()
          return float(np.sum(p * np.log(p / q)))
      ```

    - `calculate_implied_probability(self, market_a: Dict, market_b: Dict, relationship: str) -> float` — Calcula la probabilidad implícita que market_b **debería** tener dada la probabilidad de market_a y la relación entre ellos:
      - Si `relationship == "prerequisite"`: `P(B) <= P(A)` siempre (no puedes ganar la general sin ganar la primaria). La probabilidad coherente es `P(B) = P(A) × P(B|A)` donde `P(B|A)` se estima históricamente o con LLM
      - Si `relationship == "correlated"`: Usa coeficiente de correlación estimado. Si la correlación es 0.8 y A está a 70%, B debería estar entre 60-80%
      - Si `relationship == "temporal_sequence"`: Si "BTC > 100k en Q3" está a 30%, "BTC > 100k en Q4" debe ser >= 30% (el Q4 incluye el Q3)
      - Si `relationship == "same_entity"`: Compara directamente con LLM para estimar coherencia

    - `scan_arbitrage(self, min_kl: float = 0.15, min_edge_usd: float = 0.05) -> List[ArbitrageOpportunity]`— Escaneo completo:
      1. Obtiene mercados activos de Polymarket
      2. Descubre pares relacionados
      3. Calcula KL-divergence para cada par
      4. Si KL > threshold → calcula implied probability → calcula edge
      5. Retorna oportunidades ordenadas por edge descendente
      - **Dataclass de retorno**:
        ```python
        @dataclass
        class ArbitrageOpportunity:
            market_a: Dict            # Mercado A (referencia)
            market_b: Dict            # Mercado B (mispriced)
            relationship: str         # Tipo de relación
            kl_divergence: float      # Magnitud de la inconsistencia
            market_b_price: float     # Precio actual de B
            implied_price: float      # Precio que B debería tener
            edge: float               # implied_price - market_b_price
            direction: str            # "BUY" o "SELL" en market B
            confidence: str           # "high", "medium", "low"
            reasoning: str            # Explicación de por qué son inconsistentes
        ```

    - `monitor_convergence(self, opportunity: ArbitrageOpportunity) -> Dict` — Tras entrar en un trade de arbitraje, monitorea si los precios convergen. Calcula P&L no realizado

  - **Integración con el sistema existente**:
    - Se añade como herramienta nueva al `TradingEngine` (T-017): `run_cycle()` primero ejecuta `kl_scanner.scan_arbitrage()` (rápido, segundos) y luego el análisis de enjambre completo (lento, minutos) solo si no hay oportunidades de arbitraje
    - Nuevo endpoint: `GET /api/polymarket/arbitrage` → lista de oportunidades detectadas
    - Nuevo componente Vue: card de "Arbitrage Opportunities" en el MarketScanner

  - **Por qué es la estrategia de menor riesgo**:
    - No depende de que tu `model_p` sea correcto
    - Explota inconsistencias **internas** del mercado, no predicciones sobre el mundo
    - Historicamente, los fondos que más ganaron en Polymarket 2024-2025 usaban esta estrategia en mercados políticos correlacionados
    - El edge no viene de ser más listo que el mercado, sino de que **dos mercados no se han ajustado entre sí**

  - **Ejemplo concreto**:
    ```
    Market A: "Trump gana la nominación republicana" → precio 0.75 (75%)
    Market B: "Trump gana la elección general"       → precio 0.60 (60%)

    Relación: B es prerequisito de A (para ganar la general, primero necesita la nominación)
    Históricamente: P(general | nominación) ≈ 0.85 para candidatos con este perfil

    Implied price de B: 0.75 × 0.85 = 0.6375
    Precio actual de B: 0.60
    Edge: +0.0375 (3.75%)

    KL-divergence: 0.021 (bajo — los mercados son casi coherentes)
    → No hay trade (KL < 0.15)

    Pero si B estuviera a 0.45:
    Edge: +0.1875 (18.75%)
    KL-divergence: 0.31 (alto — incoherencia significativa)
    → BUY B (infravalorado respecto a A)
    ```

  - **Dependencia**: T-006 (connector para datos de mercado). No necesita enjambre, grafo, ni simulación
  - **Criterio de completado**: `scanner.scan_arbitrage()` identifica al menos 1 par inconsistente en mercados reales de Polymarket (o retorna lista vacía justificada si no hay ninguno)

- [ ] **T-042** — Sistema de Actualización Bayesiana Incremental
  - **Descripcion**: Sistema que actualiza las estimaciones de probabilidad de forma incremental cuando llega nueva información, en vez de re-ejecutar el pipeline completo (ontología + grafo + simulación). Implementa Bayes continuo: cada nueva pieza de evidencia actualiza el **prior** existente en vez de empezar desde cero. Esto reduce el coste de ~$2.50 y ~20 minutos por update a ~$0.05 y ~30 segundos.
  - **Archivo nuevo**: `backend/app/services/polymarket/bayesian_updater.py`

  - **Concepto matemático**:

    Teorema de Bayes aplicado a actualizaciones incrementales:

    ```
    P(H|E) = P(E|H) · P(H) / P(E)

    Donde:
      P(H)   = prior (probabilidad actual estimada por el sistema)
      P(E|H) = likelihood (probabilidad de ver esta evidencia SI el evento ocurre)
      P(E)   = marginal (probabilidad de ver esta evidencia en general)
      P(H|E) = posterior (nueva probabilidad después de incorporar la evidencia)
    ```

    **El ciclo continuo**:
    ```
    Análisis inicial (enjambre completo) → prior₀ = 0.55
      ↓
    Nueva noticia llega (RSS/NewsAPI detect)
      ↓
    LLM estima likelihoods: P(noticia|YES) = 0.80, P(noticia|NO) = 0.30
      ↓
    Bayes update: posterior₁ = (0.80 × 0.55) / ((0.80 × 0.55) + (0.30 × 0.45))
                             = 0.44 / (0.44 + 0.135)
                             = 0.765
      ↓
    prior₁ = 0.765 (nuevo prior para el siguiente update)
      ↓
    Otra noticia llega...
      ↓
    Bayes update: posterior₂ = ...
    ```

    Cada update es **O(1)** — una multiplicación y una normalización. No necesita reconstruir el grafo ni re-simular.

  - **Clase**: `BayesianUpdater`
  - **Metodos a implementar**:

    - `__init__(self, market_id: str, initial_estimate: MarketEstimate)` — Inicializa con el resultado del análisis de enjambre como prior. Guarda el historial de updates

    - `estimate_likelihoods(self, evidence_text: str, hypothesis: str) -> Tuple[float, float]` — **Método central**. Dado un texto de evidencia nueva (noticia, tweet, dato), usa LLM para estimar:
      - `P(evidence | outcome=YES)` — ¿Qué tan probable es ver esta evidencia si el evento SÍ ocurre?
      - `P(evidence | outcome=NO)` — ¿Qué tan probable es ver esta evidencia si el evento NO ocurre?

      El prompt al LLM es crítico. Debe ser:
      ```
      Eres un analista de probabilidad. Dado el siguiente evento de predicción:
      "{hypothesis}"

      Y la siguiente nueva evidencia:
      "{evidence_text}"

      Estima dos valores (responde SOLO con dos números separados por coma):
      1. P(esta evidencia | el evento SÍ ocurre) — del 0.0 al 1.0
      2. P(esta evidencia | el evento NO ocurre) — del 0.0 al 1.0

      Ejemplo: si la evidencia es muy consistente con que el evento ocurra,
      podrías responder "0.85, 0.20"

      Si la evidencia es irrelevante para el evento, responde "0.50, 0.50"
      ```

      Coste: ~$0.01 por call con gpt-4o-mini. Latencia: ~1-2 segundos

    - `update(self, evidence_text: str, evidence_source: str = "unknown") -> BayesianUpdate` — Ejecuta un update Bayesiano completo:
      1. Estima likelihoods con LLM
      2. Aplica Bayes: `posterior = (like_yes * prior) / (like_yes * prior + like_no * (1 - prior))`
      3. Aplica **dampening** para evitar updates demasiado agresivos: `dampened_posterior = prior + damping_factor * (posterior - prior)` donde `damping_factor = 0.7` (evita que una sola noticia mueva la estimación de 55% a 95%)
      4. Registra el update en el historial
      5. Retorna dataclass con detalle

      **Dataclass**:
      ```python
      @dataclass
      class BayesianUpdate:
          update_id: str
          timestamp: str
          evidence_text: str         # Texto de la evidencia
          evidence_source: str       # "rss", "newsapi", "twitter", "manual"
          prior: float               # Probabilidad antes del update
          likelihood_yes: float      # P(evidence | YES)
          likelihood_no: float       # P(evidence | NO)
          raw_posterior: float       # Posterior sin dampening
          dampened_posterior: float   # Posterior con dampening (este se usa)
          likelihood_ratio: float    # P(E|H) / P(E|¬H) — fuerza de la evidencia
          shift: float               # dampened_posterior - prior (cuánto cambió)
      ```

    - `batch_update(self, evidence_list: List[Dict]) -> List[BayesianUpdate]` — Aplica múltiples updates secuencialmente. El posterior de uno se convierte en el prior del siguiente. Ordena por timestamp para respetar cronología

    - `get_current_estimate(self) -> float` — Retorna la probabilidad posterior más reciente

    - `get_update_history(self) -> List[BayesianUpdate]` — Historial completo de updates. Útil para visualizar cómo evolucionó la estimación con cada pieza de evidencia

    - `should_full_reanalysis(self) -> bool` — Detecta cuándo los updates incrementales ya no son suficientes y hay que re-ejecutar el análisis de enjambre completo. Triggers:
      - Más de 20 updates acumulados (drift acumulado puede ser significativo)
      - Shift total desde el análisis original > 0.30 (la situación cambió radicalmente)
      - Última re-análisis hace más de 72 horas
      - Evidencia contradictoria fuerte (likelihood_ratio > 5.0 o < 0.2)

    - `_save_state(self)` / `_load_state(self)` — Persistencia en `uploads/polymarket/bayesian/<market_id>.json`

  - **Integración con el sistema existente**:

    El flujo actual del bot es:
    ```
    ANTES (sin Bayes):
    Cada ciclo (30 min) → full_analysis() → 20 min + $2.50 → trade decision

    DESPUÉS (con Bayes):
    Primer ciclo → full_analysis() → 20 min + $2.50 → prior₀
    Cada ciclo siguiente:
      1. news_ingestor.fetch_all() → nuevas noticias desde último check
      2. Filtrar solo noticias NUEVAS (no vistas antes)
      3. Para cada noticia nueva: bayesian_updater.update(noticia)
      4. Si should_full_reanalysis() → full_analysis() (raro, cada 1-3 días)
      5. Sino → usar get_current_estimate() como model_p → 30 seg + $0.05
    ```

    Esto convierte el bot de "analiza 2-3 mercados/día" a "monitorea 20-30 mercados continuamente".

    - Se modifica `TradingEngine.run_cycle()` (T-017) para usar Bayesian updates como default y full analysis solo cuando el updater lo pide
    - Se modifica `probability_engine.py` (T-015) para guardar el `MarketEstimate` como initial prior del updater
    - Nuevo endpoint: `GET /api/polymarket/analysis/<market_id>/history` → historial de updates Bayesianos
    - Nuevo componente Vue: gráfico temporal en `MarketAnalysis.vue` mostrando cómo evolucionó la probabilidad con cada update

  - **Ventajas clave**:
    - **Velocidad**: 30 segundos vs 20 minutos. Puedes reaccionar a noticias antes de que el mercado ajuste
    - **Coste**: $0.05 vs $2.50 por update. Puedes monitorear 50x más mercados con el mismo presupuesto
    - **Traceabilidad**: Cada cambio en la estimación está vinculado a una evidencia concreta. Puedes hacer post-mortem: "¿qué noticia me hizo mover de 55% a 76% y estaba justificado?"
    - **Combina lo mejor de ambos mundos**: El enjambre da una estimación inicial de alta calidad (costosa pero profunda), Bayes la mantiene actualizada con bajo coste

  - **Riesgos y mitigaciones**:
    - **LLM estima mal las likelihoods**: Dampening factor (0.7) limita el impacto de cualquier update individual. Ninguna noticia puede mover la estimación más de ~20% de golpe
    - **Drift acumulado**: `should_full_reanalysis()` detecta cuándo re-calibrar con el enjambre completo
    - **Noticias duplicadas**: Deduplicación ya implementada en `NewsIngestor` (T-007)
    - **Noticias irrelevantes**: Si LLM estima likelihoods 0.50/0.50 (evidencia irrelevante), el update Bayesiano no mueve nada — es self-correcting

  - **Ejemplo concreto paso a paso**:
    ```
    Mercado: "¿Aprobará la SEC un ETF de Ethereum spot antes de julio 2026?"

    Análisis inicial (enjambre):
      prior₀ = 0.42, confidence = 0.68

    Update 1 — RSS captura: "SEC solicita comentarios públicos sobre propuesta de ETF ETH"
      P(noticia | YES) = 0.85 (muy probable si van a aprobar)
      P(noticia | NO)  = 0.40 (también posible como trámite)
      Likelihood ratio = 2.125
      Raw posterior = 0.508
      Dampened posterior = 0.42 + 0.7 × (0.508 - 0.42) = 0.482
      → prior₁ = 0.482 (+6.2 puntos)

    Update 2 — NewsAPI: "BlackRock actualiza prospecto de ETF ETH con fecha tentativa"
      P(noticia | YES) = 0.90
      P(noticia | NO)  = 0.15
      Likelihood ratio = 6.0
      Raw posterior = 0.848
      Dampened posterior = 0.482 + 0.7 × (0.848 - 0.482) = 0.738
      → prior₂ = 0.738 (+25.6 puntos)
      → should_full_reanalysis() = True (shift > 0.30 desde original)

    Update 3 — Twitter: "Gensler dice en entrevista que 'no hay timeline para ETFs de cripto'"
      P(noticia | YES) = 0.25
      P(noticia | NO)  = 0.80
      Likelihood ratio = 0.3125
      Raw posterior = 0.468
      Dampened posterior = 0.738 + 0.7 × (0.468 - 0.738) = 0.549
      → prior₃ = 0.549 (-18.9 puntos)

    Resultado: En 3 updates (~90 segundos, ~$0.03), la estimación pasó de
    0.42 → 0.482 → 0.738 → 0.549, reflejando la información en tiempo real.
    El sistema flagea que necesita re-análisis completo por shift total > 0.30.
    ```

  - **Dependencia**: T-015 (full_analysis como generador del prior inicial), T-007 (news_ingestor para detectar noticias nuevas)
  - **Criterio de completado**: `updater.update("Breaking: SEC approves ETF")` mueve la probabilidad en dirección correcta en < 2 segundos. `get_update_history()` muestra la cadena de updates con likelihoods y shifts.

---

## Mapa de Dependencias entre Tareas

```
FASE 0
  T-001 (docs)          ─── independiente
  T-002 (config)         ─── independiente
  T-003 (.env.example)   ─── depende de T-002
  T-004 (requirements)   ─── independiente
  T-005 (package init)   ─── independiente

FASE 1 (requiere Fase 0)
  T-006 (connector)      ─── depende de T-002, T-004, T-005
  T-007 (news ingestor)  ─── depende de T-002, T-004, T-005
  T-008 (market ontology)─── depende de T-005
  T-009 (ontology mod)   ─── independiente
  T-010 (paper ledger)   ─── depende de T-002, T-005

FASE 2 (requiere Fase 1)
  T-011 (prepare)        ─── depende de T-006, T-007, T-008, T-009
  T-012 (agents)         ─── depende de T-011
  T-013 (simulation)     ─── depende de T-012
  T-014 (extract prob)   ─── depende de T-013
  T-015 (full analysis)  ─── depende de T-014
  T-016 (position sizer) ─── independiente dentro de Fase 2

FASE 3 (requiere Fase 2)
  T-017 (trading engine) ─── depende de T-015, T-016, T-010
  T-018 (connector live) ─── depende de T-006
  T-019 (API blueprint)  ─── depende de T-017
  T-020 (register bp)    ─── depende de T-019
  T-021 (bot script)     ─── depende de T-017

FASE 4 (requiere Fase 3)
  T-022 (api client js)  ─── depende de T-019
  T-023 (router)         ─── independiente
  T-024 (main view)      ─── depende de T-023
  T-025 (scanner)        ─── depende de T-022, T-024
  T-026 (analysis)       ─── depende de T-022, T-024
  T-027 (portfolio)      ─── depende de T-022, T-024
  T-028 (bot control)    ─── depende de T-022, T-024
  T-029 (navegacion)     ─── depende de T-023

FASE 5 (requiere Fase 4)
  T-030..T-034 (tests)   ─── depende de sus respectivos modulos
  T-035 (paper trading)  ─── depende de T-021
  T-036 (calibracion)    ─── depende de T-035
  T-037..T-040 (mejoras) ─── opcionales
  T-041 (KL scanner)     ─── depende de T-006 (solo connector, no necesita enjambre)
  T-042 (Bayes updater)  ─── depende de T-015 (full_analysis como prior), T-007 (news)
```

---

## Resumen de Archivos

### Archivos nuevos a crear (24)

| # | Archivo | Fase | Tarea |
|---|---------|------|-------|
| 1 | `docs/POLYMARKET_SETUP.md` | 0 | T-001 |
| 2 | `backend/app/services/polymarket/__init__.py` | 0 | T-005 |
| 3 | `backend/app/services/polymarket/connector.py` | 1 | T-006 |
| 4 | `backend/app/services/polymarket/news_ingestor.py` | 1 | T-007 |
| 5 | `backend/app/services/polymarket/market_ontology.py` | 1 | T-008 |
| 6 | `backend/app/services/polymarket/paper_ledger.py` | 1 | T-010 |
| 7 | `backend/app/services/polymarket/probability_engine.py` | 2 | T-011..T-015 |
| 8 | `backend/app/services/polymarket/position_sizer.py` | 2 | T-016 |
| 9 | `backend/app/services/polymarket/trading_engine.py` | 3 | T-017 |
| 10 | `backend/app/api/polymarket.py` | 3 | T-019 |
| 11 | `backend/scripts/run_polymarket_bot.py` | 3 | T-021 |
| 12 | `frontend/src/api/polymarket.js` | 4 | T-022 |
| 13 | `frontend/src/views/PolymarketView.vue` | 4 | T-024 |
| 14 | `frontend/src/components/polymarket/MarketScanner.vue` | 4 | T-025 |
| 15 | `frontend/src/components/polymarket/MarketAnalysis.vue` | 4 | T-026 |
| 16 | `frontend/src/components/polymarket/Portfolio.vue` | 4 | T-027 |
| 17 | `frontend/src/components/polymarket/BotControl.vue` | 4 | T-028 |
| 18 | `backend/tests/test_position_sizer.py` | 5 | T-030 |
| 19 | `backend/tests/test_paper_ledger.py` | 5 | T-031 |
| 20 | `backend/tests/test_connector.py` | 5 | T-032 |
| 21 | `backend/tests/test_news_ingestor.py` | 5 | T-033 |
| 22 | `backend/tests/test_e2e_polymarket.py` | 5 | T-034 |
| 23 | `backend/app/services/polymarket/kl_scanner.py` | 5 | T-041 |
| 24 | `backend/app/services/polymarket/bayesian_updater.py` | 5 | T-042 |

### Archivos existentes a modificar (5)

| # | Archivo | Fase | Tarea | Cambio |
|---|---------|------|-------|--------|
| 1 | `backend/app/config.py` | 0 | T-002 | +13 lineas config Polymarket |
| 2 | `.env.example` | 0 | T-003 | +12 lineas variables |
| 3 | `backend/requirements.txt` | 0 | T-004 | +3 lineas dependencias |
| 4 | `backend/app/services/ontology_generator.py` | 1 | T-009 | +2 lineas (param system_prompt) |
| 5 | `backend/app/api/__init__.py` | 3 | T-020 | +2 lineas (blueprint) |
| 6 | `backend/app/__init__.py` | 3 | T-020 | +2 lineas (register) |
| 7 | `frontend/src/router/index.js` | 4 | T-023 | +7 lineas (ruta) |
| 8 | `frontend/src/views/Home.vue` | 4 | T-029 | +link navegacion |
