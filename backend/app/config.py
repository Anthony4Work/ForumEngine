"""
Configuration Management
Loads configuration from the project root .env file
"""

import os
from dotenv import load_dotenv

# Load .env file from project root
# Path: MiroFish/.env (relative to backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # If no .env in root, try loading environment variables (for production)
    load_dotenv(override=True)


class Config:
    """Flask configuration class"""

    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # JSON configuration - disable ASCII escaping for direct Unicode display (instead of \uXXXX format)
    JSON_AS_ASCII = False

    # LLM configuration (unified OpenAI format)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')

    # Embedding configuration
    EMBEDDING_API_KEY = os.environ.get('EMBEDDING_API_KEY', os.environ.get('LLM_API_KEY'))
    EMBEDDING_BASE_URL = os.environ.get('EMBEDDING_URL', 'https://api.openai.com/v1')
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')

    # Neo4j / Graphiti configuration
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'neo4j-password')

    # File upload configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # Knowledge Graph Build
    DEFAULT_CHUNK_SIZE = int(os.environ.get('GRAPH_CHUNK_SIZE', '500'))
    DEFAULT_CHUNK_OVERLAP = int(os.environ.get('GRAPH_CHUNK_OVERLAP', '50'))
    GRAPH_BUILD_BATCH_SIZE = int(os.environ.get('GRAPH_BUILD_BATCH_SIZE', '3'))
    GRAPH_BUILD_BATCH_PAUSE = float(os.environ.get('GRAPH_BUILD_BATCH_PAUSE', '0.5'))
    GRAPH_MAX_ENTITY_TYPES = int(os.environ.get('GRAPH_MAX_ENTITY_TYPES', '10'))
    GRAPH_MAX_EDGE_TYPES = int(os.environ.get('GRAPH_MAX_EDGE_TYPES', '10'))
    GRAPH_ONTOLOGY_TEMPERATURE = float(os.environ.get('GRAPH_ONTOLOGY_TEMPERATURE', '0.3'))

    # Deliberation configuration
    DELIBERATION_DEFAULT_MAX_ROUNDS = int(os.environ.get('DELIBERATION_DEFAULT_MAX_ROUNDS', '25'))
    SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    # Backward compat alias
    OASIS_SIMULATION_DATA_DIR = SIMULATION_DATA_DIR

    # Concurrency configuration
    LLM_MAX_CONCURRENT = int(os.environ.get('LLM_MAX_CONCURRENT', '5'))
    DELIBERATION_PARALLEL_AGENTS = os.environ.get('DELIBERATION_PARALLEL_AGENTS', 'true').lower() == 'true'

    # SME Agents
    SME_AGENT_ENABLED = os.environ.get('SME_AGENT_ENABLED', 'true').lower() == 'true'
    SME_AGENT_COUNT = int(os.environ.get('SME_AGENT_COUNT', '5'))
    SME_VOLUNTEER_PROBABILITY = float(os.environ.get('SME_VOLUNTEER_PROBABILITY', '0.4'))

    # OASIS Feedback Loop
    OASIS_FEEDBACK_ENABLED = os.environ.get('OASIS_FEEDBACK_ENABLED', 'false').lower() == 'true'
    OASIS_FEEDBACK_ROUNDS = int(os.environ.get('OASIS_FEEDBACK_ROUNDS', '30'))
    OASIS_FEEDBACK_PLATFORM = os.environ.get('OASIS_FEEDBACK_PLATFORM', 'reddit')
    OASIS_FEEDBACK_RUN_PHASE_8 = os.environ.get('OASIS_FEEDBACK_RUN_PHASE_8', 'true').lower() == 'true'

    # Report Agent configuration
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.NEO4J_URI:
            errors.append("NEO4J_URI is not configured")
        return errors
