"""
One-off script: embeds every KnowledgeBaseArticle row into Qdrant so
search_knowledge_base (KnowledgeSearchTool) actually returns results.

Run this ONCE after the database is seeded (TicketPilot_data.sql) and
config.ini is filled in, and again any time you add/edit KB articles.

Usage (from the outer ticketpilot_das/ folder, with the venv active):
    python scripts/EmbedKnowledgeBase.py
"""
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from ticketpilot_das.ticket_management.entity.DbModels import KnowledgeBaseArticle
from ticketpilot_das.ticket_management.tools.KnowledgeSearchTool import embed_text, get_client
from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.Database import SessionLocal
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("scripts.EmbedKnowledgeBase")


def main() -> None:
    try:
        collection = Configuration.QDRANT_COLLECTION_KNOWLEDGE_BASE
        client = get_client()

        # Vector size isn't known ahead of time anymore -- there's no local
        # model to ask for its dimension. A one-off probe embedding call
        # tells us the real dimension for whatever Configuration.
        # EMBEDDING_MODEL actually returns, so this still adapts correctly
        # if the model is ever changed in config.ini.
        probe_vector = embed_text("probe")
        vector_size = len(probe_vector)

        # Explicit delete + create, not the deprecated recreate_collection --
        # in Qdrant's local/embedded mode, recreate_collection does not
        # reliably wipe the on-disk storage from a PREVIOUS run with a
        # different vector size (it can report the new dimension while the
        # actual stored vector slots are still sized for the old model),
        # which is exactly what broke the first run of this script after
        # switching off the local sentence-transformers model. Deleting the
        # collection outright before creating it fresh avoids that leftover
        # state entirely.
        if client.collection_exists(collection_name=collection):
            client.delete_collection(collection_name=collection)
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        log.info("Collection '%s' ready (dim=%s).", collection, vector_size)
    except Exception as exc:
        log.error("Failed to prepare Qdrant collection: %s", exc)
        raise

    db = SessionLocal()
    try:
        articles = db.query(KnowledgeBaseArticle).all()
        if not articles:
            log.warning("No KnowledgeBaseArticle rows found -- did you run TicketPilot_data.sql?")
            return

        points = []
        for article in articles:
            text = f"{article.KBA_Title}\n\n{article.KBA_Content}"
            vector = embed_text(text)
            points.append(PointStruct(
                id=article.KBA_Id,
                vector=vector,
                payload={"article_id": article.KBA_Id, "title": article.KBA_Title},
            ))
            article.KBA_EmbeddingSynced = True

        client.upsert(collection_name=collection, points=points)
        db.commit()
        log.info("Embedded %s knowledge-base article(s) into '%s'.", len(points), collection)
    except Exception as exc:
        log.error("Failed to embed knowledge-base articles: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
