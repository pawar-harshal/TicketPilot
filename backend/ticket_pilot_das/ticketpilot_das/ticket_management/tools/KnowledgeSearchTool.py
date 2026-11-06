"""
search_knowledge_base -- semantic search over QuickCrave's help-center
articles, via Qdrant. This is the tool that replaces old-style keyword
matching: the agent passes its OWN phrasing of what it's trying to answer,
not the customer's literal words, and gets back the closest-meaning articles
even if no words overlap.

Embeddings come from an API call, not a local model. OpenRouter's
/embeddings endpoint is OpenAI-compatible (same request/response shape as
OpenAI's own), so the same `openai` SDK already used for chat completions
(see AgentOrchestrator.call_llm) works here too -- just pointed at a
different model, with its own API key (Configuration.EMBEDDING_API_KEY),
since embeddings and chat are billed/scoped separately in config.ini even
though both go through the same OpenRouter base_url. There is no local
model loaded into memory anymore -- every embedding is a network call.

GOVERNANCE: this tool is read-only. It cannot write, and it is not scoped
to a customer (knowledge-base articles aren't customer data), so there is
nothing here for the agent to misuse beyond reading public help content.
"""
from openai import OpenAI
from qdrant_client import QdrantClient

from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.CommonEnums import ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.KnowledgeSearchTool")

TOOL_NAME = ToolName.SEARCH_KNOWLEDGE_BASE.value

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Semantic search over QuickCrave's help-center articles. "
                       "Pass a short description of what you're trying to find out "
                       "(your own words, not necessarily the customer's).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."},
            },
            "required": ["query"],
        },
    },
}

client = None
embed_client = None


def get_client() -> QdrantClient:
    """Qdrant in LOCAL/EMBEDDED mode -- no server, no Docker, no account.
    Qdrant writes its index straight to a folder on disk (Configuration.
    QDRANT_PATH). This is the zero-setup option; swap to a host/port
    server (a real Qdrant server or Qdrant Cloud) later just by changing
    config.ini, nothing in code."""
    global client
    if client is None:
        try:
            if Configuration.QDRANT_PATH:
                log.info("Qdrant running in local/embedded mode at '%s'.", Configuration.QDRANT_PATH)
                client = QdrantClient(path=Configuration.QDRANT_PATH)
            else:
                log.info("Qdrant connecting to server at %s:%s.", Configuration.QDRANT_HOST, Configuration.QDRANT_PORT)
                client = QdrantClient(
                    host=Configuration.QDRANT_HOST,
                    port=Configuration.QDRANT_PORT,
                    api_key=Configuration.QDRANT_API_KEY,
                )
        except Exception as exc:
            log.error("Failed to connect to Qdrant: %s", exc)
            raise
    return client


def get_embed_client() -> OpenAI:
    """A separate OpenAI-SDK client from the one AgentOrchestrator.call_llm
    uses for chat -- same base_url (OpenRouter), but its own API key, kept
    distinct in config.ini so embeddings traffic/billing is separately
    identifiable from chat traffic even on the same OpenRouter account."""
    global embed_client
    if embed_client is None:
        embed_client = OpenAI(base_url=Configuration.LLM_BASE_URL, api_key=Configuration.EMBEDDING_API_KEY)
    return embed_client


def embed_text(text: str) -> list:
    response = get_embed_client().embeddings.create(model=Configuration.EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def run(query: str) -> dict:
    try:
        log.debug("search_knowledge_base query: %s", query)
        vector = embed_text(query)
    except Exception as exc:
        log.error("Embedding call failed for query '%s': %s", query, exc)
        return {"results": [], "note": "Knowledge base search is not available right now."}

    try:
        response = get_client().query_points(
            collection_name=Configuration.QDRANT_COLLECTION_KNOWLEDGE_BASE, query=vector, limit=3
        )
        hits = response.points
        log.debug("search_knowledge_base returned %s hit(s).", len(hits))
        return {
            "results": [
                {
                    "article_id": hit.payload.get("article_id"),
                    "title": hit.payload.get("title"),
                    "score": hit.score,
                }
                for hit in hits
            ]
        }
    except Exception as exc:
        log.error("Qdrant search failed for query '%s': %s", query, exc)
        return {"results": [], "note": "Knowledge base search is not available right now."}
