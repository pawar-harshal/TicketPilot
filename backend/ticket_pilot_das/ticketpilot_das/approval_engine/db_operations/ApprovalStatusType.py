"""
Name<->id cache for the ApprovalStatusType master table, built once at app
startup (see TicketPilotDas.lifespan). Same pattern as
ticket_management/db_operations/TicketStatusType.py -- see that file's
docstring for why this exists.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.approval_engine.entity.DbModels import ApprovalStatusType

_APPROVAL_STATUS_ID_BY_NAME: Dict[str, int] = {}
_APPROVAL_STATUS_NAME_BY_ID: Dict[int, str] = {}


class ApprovalStatusTypeNotFoundError(Exception):
    """Raised when a name/id is asked for that was never seeded into
    ApprovalStatusType -- this means the seed data and
    CommonEnums.ApprovalStatus are out of sync, which is a setup bug, not
    a normal runtime error."""


def load_approval_status_cache(db: Session) -> None:
    """Reads every row of ApprovalStatusType once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _APPROVAL_STATUS_ID_BY_NAME.clear()
    _APPROVAL_STATUS_NAME_BY_ID.clear()
    for row in db.query(ApprovalStatusType).all():
        _APPROVAL_STATUS_ID_BY_NAME[row.APST_Name] = row.APST_Id
        _APPROVAL_STATUS_NAME_BY_ID[row.APST_Id] = row.APST_Name


def get_cached_approval_status_id_by_name(name: str) -> int:
    try:
        return _APPROVAL_STATUS_ID_BY_NAME[name]
    except KeyError:
        raise ApprovalStatusTypeNotFoundError(
            f"ApprovalStatusType '{name}' is not in the cache -- is it seeded in ApprovalStatusType and "
            f"spelled exactly like CommonEnums.ApprovalStatus?"
        )


def get_cached_approval_status_name_by_id(status_id: int) -> str:
    try:
        return _APPROVAL_STATUS_NAME_BY_ID[status_id]
    except KeyError:
        raise ApprovalStatusTypeNotFoundError(f"ApprovalStatusType id {status_id} is not in the cache.")
