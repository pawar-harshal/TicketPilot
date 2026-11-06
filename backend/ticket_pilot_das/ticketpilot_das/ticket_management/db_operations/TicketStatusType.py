"""
Name<->id cache for the TicketStatusType master table, built once at app
startup (see TicketPilotDas.lifespan). Mirrors the reference pattern in
mw_job_creator/job_execution_state/db_operations/MWJobExecutionState.py:
business code never hardcodes a TST_Id, it resolves it by name through
this cache instead of querying TicketStatusType on every call.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.entity.DbModels import TicketStatusType

_TICKET_STATUS_ID_BY_NAME: Dict[str, int] = {}
_TICKET_STATUS_NAME_BY_ID: Dict[int, str] = {}


class TicketStatusTypeNotFoundError(Exception):
    """Raised when a name/id is asked for that was never seeded into
    TicketStatusType -- this means the seed data and CommonEnums.TicketStatus
    are out of sync, which is a setup bug, not a normal runtime error."""


def load_ticket_status_cache(db: Session) -> None:
    """Reads every row of TicketStatusType once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _TICKET_STATUS_ID_BY_NAME.clear()
    _TICKET_STATUS_NAME_BY_ID.clear()
    for row in db.query(TicketStatusType).all():
        _TICKET_STATUS_ID_BY_NAME[row.TST_Name] = row.TST_Id
        _TICKET_STATUS_NAME_BY_ID[row.TST_Id] = row.TST_Name


def get_cached_ticket_status_id_by_name(name: str) -> int:
    try:
        return _TICKET_STATUS_ID_BY_NAME[name]
    except KeyError:
        raise TicketStatusTypeNotFoundError(
            f"TicketStatusType '{name}' is not in the cache -- is it seeded in TicketStatusType and spelled "
            f"exactly like CommonEnums.TicketStatus?"
        )


def get_cached_ticket_status_name_by_id(status_id: int) -> str:
    try:
        return _TICKET_STATUS_NAME_BY_ID[status_id]
    except KeyError:
        raise TicketStatusTypeNotFoundError(f"TicketStatusType id {status_id} is not in the cache.")
