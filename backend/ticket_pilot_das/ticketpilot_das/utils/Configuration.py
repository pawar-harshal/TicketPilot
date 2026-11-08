"""
Reads config.ini ONCE at import time and converts every value to its
proper type ONCE, exposing plain module-level constants.

Every other file in the codebase imports THIS module and uses its
constants directly (e.g. Configuration.DATABASE_HOST) -- nothing else
calls ConfigReader directly or repeats a str()/int()/bool() conversion.
This mirrors how the reference auth-server's configuration.py works:
one module, one load, one set of typed constants used everywhere else.

ENVIRONMENT values additionally check an OS environment variable of the
SAME name first (e.g. DATABASE_PASSWORD), falling back to config.ini only
if that variable isn't set. This is what lets a "<service>.env" file,
injected by Docker Compose's env_file: at container startup, override a
secret without it ever being committed in config.ini. GENERAL values are
never overridden this way -- same split as the reference.
"""
import os

from ticketpilot_das.utils import ConfigReader
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("utils.Configuration")

# Package root (the ticketpilot_das/ folder) -- same base ConfigReader uses
# to find data/config.ini, reused here to find data/prompts/.
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_PROMPT_PATH = os.environ.get(
    "TICKETPILOT_SYSTEM_PROMPT_PATH",
    os.path.join(_PACKAGE_ROOT, "data", "prompts", "system_prompt.txt"),
)

try:
    GENERAL = ConfigReader.get_section("GENERAL")
    ENVIRONMENT = ConfigReader.get_section("ENVIRONMENT")

    # -----------------------------------------------------------------
    # GENERAL -- behavior/algorithm settings, the same on any machine.
    # File-only, never overridden by an environment variable.
    # -----------------------------------------------------------------
    JWT_ALGORITHM = str(GENERAL["jwt_algorithm"])
    JWT_EXPIRY_MINUTES = int(GENERAL["jwt_expiry_minutes"])
    MAX_TOOL_CALLS = int(GENERAL["max_tool_calls"])

    LLM_MODEL = str(GENERAL["llm_model"])
    LLM_BASE_URL = str(GENERAL["llm_base_url"])

    # Retry settings for a transient (rate-limit) failure calling the LLM --
    # same retry mechanism as the reference codebase (retrying + exponential
    # backoff), see AgentOrchestrator.call_llm.
    LLM_RETRY_ATTEMPTS = int(GENERAL["llm_retry_attempts"])
    LLM_RETRY_WAIT_MULTIPLIER_MS = int(GENERAL["llm_retry_wait_multiplier_ms"])
    LLM_RETRY_MAX_WAIT_MS = int(GENERAL["llm_retry_max_wait_ms"])

    EMBEDDING_MODEL = str(GENERAL["embedding_model"])

    QDRANT_COLLECTION_KNOWLEDGE_BASE = str(GENERAL["qdrant_collection_knowledge_base"])

    LOGGING_LEVEL = str(GENERAL["logging_level"])

    AUTO_CREATE_TABLES = GENERAL["auto_create_tables"].strip().lower() == "true"

    # How often (minutes) the backend automatically calls sp_reset_demo()
    # on its own, in addition to the manager's manual "Reset Demo Data"
    # button -- keeps the public demo clean without anyone having to
    # remember to press it. Fixed-interval, not idle-based: it fires on
    # this clock regardless of whether someone is mid-demo. See
    # TicketPilotDas.py's _auto_reset_demo_loop().
    DEMO_AUTO_RESET_MINUTES = int(GENERAL["demo_auto_reset_minutes"])

    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()

    # -----------------------------------------------------------------
    # ENVIRONMENT -- this machine/deployment's own settings and secrets.
    # Each one checks os.environ[SAME_NAME] first, falls back to
    # config.ini if that variable isn't set.
    # -----------------------------------------------------------------
    DATABASE_HOST = os.environ.get("DATABASE_HOST", ENVIRONMENT["database_host"])
    DATABASE_PORT = int(os.environ.get("DATABASE_PORT", ENVIRONMENT["database_port"]))
    DATABASE_NAME = os.environ.get("DATABASE_NAME", ENVIRONMENT["database_name"])
    DATABASE_USER = os.environ.get("DATABASE_USER", ENVIRONMENT["database_user"])
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD", ENVIRONMENT["database_password"])

    QDRANT_PATH = os.environ.get("QDRANT_PATH", ENVIRONMENT["qdrant_path"]).strip() or None
    QDRANT_HOST = os.environ.get("QDRANT_HOST", ENVIRONMENT["qdrant_host"]).strip() or None
    qdrant_port_value = os.environ.get("QDRANT_PORT", ENVIRONMENT["qdrant_port"])
    QDRANT_PORT = int(qdrant_port_value) if qdrant_port_value.strip() else None
    QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", ENVIRONMENT["qdrant_api_key"]).strip() or None

    LLM_API_KEY = os.environ.get("LLM_API_KEY", ENVIRONMENT["llm_api_key"]).strip() or None
    EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", ENVIRONMENT["embedding_api_key"]).strip() or None

    JWT_SECRET = os.environ.get("JWT_SECRET", ENVIRONMENT["jwt_secret"])

    SERVER_HOST = os.environ.get("SERVER_HOST", ENVIRONMENT["server_host"])
    SERVER_PORT = int(os.environ.get("SERVER_PORT", ENVIRONMENT["server_port"]))

    log.info("Configuration loaded successfully from config.ini (with any env-var overrides applied).")

except KeyError as exc:
    log.error("Configuration is missing a required key: %s", exc)
    raise
except Exception as exc:
    log.error("Unexpected error while loading configuration: %s", exc)
    raise