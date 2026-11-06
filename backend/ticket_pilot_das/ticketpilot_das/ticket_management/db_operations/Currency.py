"""
Name<->id cache for the Currency master table, built once at app startup
(see TicketPilotDas.lifespan). Same pattern as TicketStatusType.py -- see
that file's docstring for why this exists. Resolution here is by CUR_Code
(e.g. "INR"), not by a human-readable name, since that's what
CommonEnums.CurrencyCode holds.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.entity.DbModels import Currency

_CURRENCY_ID_BY_CODE: Dict[str, int] = {}
_CURRENCY_CODE_BY_ID: Dict[int, str] = {}


class CurrencyNotFoundError(Exception):
    """Raised when a code/id is asked for that was never seeded into
    Currency -- this means the seed data and CommonEnums.CurrencyCode are
    out of sync, which is a setup bug, not a normal runtime error."""


def load_currency_cache(db: Session) -> None:
    """Reads every row of Currency once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _CURRENCY_ID_BY_CODE.clear()
    _CURRENCY_CODE_BY_ID.clear()
    for row in db.query(Currency).all():
        _CURRENCY_ID_BY_CODE[row.CUR_Code] = row.CUR_Id
        _CURRENCY_CODE_BY_ID[row.CUR_Id] = row.CUR_Code


def get_cached_currency_id_by_code(code: str) -> int:
    try:
        return _CURRENCY_ID_BY_CODE[code]
    except KeyError:
        raise CurrencyNotFoundError(
            f"Currency '{code}' is not in the cache -- is it seeded in Currency and spelled exactly like "
            f"CommonEnums.CurrencyCode?"
        )


def get_cached_currency_code_by_id(currency_id: int) -> str:
    try:
        return _CURRENCY_CODE_BY_ID[currency_id]
    except KeyError:
        raise CurrencyNotFoundError(f"Currency id {currency_id} is not in the cache.")
