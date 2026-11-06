"""
Name<->id cache for the MessageSenderType master table, built once at app
startup (see TicketPilotDas.lifespan). Same pattern as TicketStatusType.py
-- see that file's docstring for why this exists.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.entity.DbModels import MessageSenderType

_SENDER_ID_BY_NAME: Dict[str, int] = {}
_SENDER_NAME_BY_ID: Dict[int, str] = {}


class MessageSenderTypeNotFoundError(Exception):
    """Raised when a name/id is asked for that was never seeded into
    MessageSenderType -- this means the seed data and
    CommonEnums.TicketMessageSender are out of sync, which is a setup bug,
    not a normal runtime error."""


def load_message_sender_cache(db: Session) -> None:
    """Reads every row of MessageSenderType once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _SENDER_ID_BY_NAME.clear()
    _SENDER_NAME_BY_ID.clear()
    for row in db.query(MessageSenderType).all():
        _SENDER_ID_BY_NAME[row.MST_Name] = row.MST_Id
        _SENDER_NAME_BY_ID[row.MST_Id] = row.MST_Name


def get_cached_message_sender_id_by_name(name: str) -> int:
    try:
        return _SENDER_ID_BY_NAME[name]
    except KeyError:
        raise MessageSenderTypeNotFoundError(
            f"MessageSenderType '{name}' is not in the cache -- is it seeded in MessageSenderType and spelled "
            f"exactly like CommonEnums.TicketMessageSender?"
        )


def get_cached_message_sender_name_by_id(sender_id: int) -> str:
    try:
        return _SENDER_NAME_BY_ID[sender_id]
    except KeyError:
        raise MessageSenderTypeNotFoundError(f"MessageSenderType id {sender_id} is not in the cache.")
