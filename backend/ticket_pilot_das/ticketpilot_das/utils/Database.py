"""
Single shared SQLAlchemy engine/session/Base for the whole package.

Every module's entity/DbModels.py imports `Base` from here so that all
tables end up registered on the same metadata object (needed for
create_all() during local dev, and for Alembic later if we add it).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("utils.Database")

Base = declarative_base()

DB_URL = (
    f"mysql+pymysql://{Configuration.DATABASE_USER}:{Configuration.DATABASE_PASSWORD}"
    f"@{Configuration.DATABASE_HOST}:{Configuration.DATABASE_PORT}/{Configuration.DATABASE_NAME}"
)

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """FastAPI dependency: yields a session, always closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        log.error("Database session raised an error, rolling back: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()
