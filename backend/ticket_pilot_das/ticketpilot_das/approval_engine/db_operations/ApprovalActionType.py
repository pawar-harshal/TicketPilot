"""
Name<->id cache for the ApprovalActionType master table, built once at app
startup (see TicketPilotDas.lifespan). Same pattern as
ticket_management/db_operations/TicketStatusType.py -- see that file's
docstring for why this exists.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.approval_engine.entity.DbModels import ApprovalActionType

_APPROVAL_ACTION_ID_BY_NAME: Dict[str, int] = {}
_APPROVAL_ACTION_NAME_BY_ID: Dict[int, str] = {}


class ApprovalActionTypeNotFoundError(Exception):
    """Raised when a name/id is asked for that was never seeded into
    ApprovalActionType -- this means the seed data and
    CommonEnums.ApprovalActionType are out of sync, which is a setup bug,
    not a normal runtime error."""


def load_approval_action_cache(db: Session) -> None:
    """Reads every row of ApprovalActionType once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _APPROVAL_ACTION_ID_BY_NAME.clear()
    _APPROVAL_ACTION_NAME_BY_ID.clear()
    for row in db.query(ApprovalActionType).all():
        _APPROVAL_ACTION_ID_BY_NAME[row.APAT_Name] = row.APAT_Id
        _APPROVAL_ACTION_NAME_BY_ID[row.APAT_Id] = row.APAT_Name


def get_cached_approval_action_id_by_name(name: str) -> int:
    try:
        return _APPROVAL_ACTION_ID_BY_NAME[name]
    except KeyError:
        raise ApprovalActionTypeNotFoundError(
            f"ApprovalActionType '{name}' is not in the cache -- is it seeded in ApprovalActionType and "
            f"spelled exactly like CommonEnums.ApprovalActionType?"
        )


def get_cached_approval_action_name_by_id(action_id: int) -> str:
    try:
        return _APPROVAL_ACTION_NAME_BY_ID[action_id]
    except KeyError:
        raise ApprovalActionTypeNotFoundError(f"ApprovalActionType id {action_id} is not in the cache.")
