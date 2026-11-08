"""
TicketPilot FastAPI entrypoint. Run with:

    python -m ticketpilot_das.TicketPilotDas

(host/port come from config.ini's ENVIRONMENT section)

For local development with auto-reload while editing, run instead via:

    uvicorn ticketpilot_das.TicketPilotDas:app --reload --log-config=null

The --log-config=null flag matters: without it, the uvicorn CLI applies its
own default console logging config, which can undo the file-only logging
Logger.py sets up (see the log_config=None comment on uvicorn.run() below
for the same reason, for the `python -m` path).
"""
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from ticketpilot_das.approval_engine.db_operations.ApprovalActionType import load_approval_action_cache
from ticketpilot_das.approval_engine.db_operations.ApprovalStatusType import load_approval_status_cache
from ticketpilot_das.approval_engine.routes.Approval import router as approval_router
from ticketpilot_das.auth.routes.Auth import router as auth_router
from ticketpilot_das.ticket_management.db_operations.Currency import load_currency_cache
from ticketpilot_das.ticket_management.db_operations.MessageSenderType import load_message_sender_cache
from ticketpilot_das.ticket_management.db_operations.OrderStatusType import load_order_status_cache
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import load_ticket_status_cache
from ticketpilot_das.ticket_management.routes.Ticket import router as ticket_router
from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.Database import Base, SessionLocal, engine
from ticketpilot_das.utils.Logger import get_logger

# Import every module's DbModels so their tables register on Base.metadata
# before create_all() runs below.
import ticketpilot_das.approval_engine.entity.DbModels  # noqa: F401
import ticketpilot_das.auth.entity.DbModels  # noqa: F401
import ticketpilot_das.ticket_management.entity.DbModels  # noqa: F401

log = get_logger("main")


async def _auto_reset_demo_loop():
    """
    Background task: calls the same sp_reset_demo() stored procedure the
    manager's manual "Reset Demo Data" button uses (see routes/Ticket.py's
    resetDemo endpoint), on a fixed interval (Configuration.DEMO_AUTO_RESET_MINUTES),
    so the public demo stays clean without anyone having to press the button.

    Fixed-interval, not idle-based: it fires on this clock regardless of
    whether someone is mid-demo at that moment -- a deliberate simplicity
    tradeoff, not an oversight.

    Runs forever until cancelled (see lifespan's shutdown below). A single
    failed reset is logged and the loop keeps going -- one bad iteration
    shouldn't permanently stop future resets.
    """
    interval_seconds = Configuration.DEMO_AUTO_RESET_MINUTES * 60
    log.info("Auto-reset loop starting -- resetting demo data every %s minutes.", Configuration.DEMO_AUTO_RESET_MINUTES)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            db = SessionLocal()
            try:
                db.execute(text("CALL sp_reset_demo();"))
                db.commit()
                log.info("Auto-reset: demo data reset successfully.")
            except Exception as exc:
                db.rollback()
                log.error("Auto-reset: sp_reset_demo() failed: %s", exc)
            finally:
                db.close()
        except asyncio.CancelledError:
            log.info("Auto-reset loop stopping (app shutting down).")
            raise
        except Exception as exc:
            # Guards the sleep/loop machinery itself, not just the DB call
            # above -- so one unexpected error here can't silently kill
            # future resets for the rest of the process's life.
            log.error("Auto-reset loop hit an unexpected error, will retry next cycle: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if Configuration.AUTO_CREATE_TABLES:
            log.info("auto_create_tables is on -- creating any missing tables.")
            Base.metadata.create_all(bind=engine)
        else:
            log.info("auto_create_tables is off -- expecting tables to already exist.")
    except Exception as exc:
        log.error("Startup table-creation check failed: %s", exc)
        raise

    # Build every master-table name<->id cache ONCE here, before the app
    # starts taking requests -- see each cache module's docstring for why
    # (mirrors mw_job_creator's load_execution_state_cache() pattern).
    try:
        log.info("Loading master-table caches.")
        db = SessionLocal()
        try:
            load_ticket_status_cache(db)
            load_order_status_cache(db)
            load_message_sender_cache(db)
            load_currency_cache(db)
            load_approval_status_cache(db)
            load_approval_action_cache(db)
        finally:
            db.close()
        log.info("Master-table caches loaded.")
    except Exception as exc:
        log.error("Failed to load master-table caches: %s", exc)
        raise

    auto_reset_task = asyncio.create_task(_auto_reset_demo_loop())

    yield

    auto_reset_task.cancel()
    try:
        await auto_reset_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="TicketPilot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ticket_router)
app.include_router(approval_router)
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # log_config=None is required here -- without it, uvicorn.run() applies
    # its OWN default logging setup (console handlers on the "uvicorn",
    # "uvicorn.error", "uvicorn.access" loggers) after Logger.configure_once()
    # already ran (triggered above by `log = get_logger("main")` at import
    # time), which would silently re-add console output and undo the
    # file-only logging Logger.py just configured. With it, uvicorn leaves
    # Python's existing logging setup alone.
    uvicorn.run(
        app,
        host=Configuration.SERVER_HOST,
        port=Configuration.SERVER_PORT,
        log_config=None,
    )