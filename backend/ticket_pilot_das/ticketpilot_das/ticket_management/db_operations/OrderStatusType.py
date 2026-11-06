"""
Name<->id cache for the OrderStatusType master table, built once at app
startup (see TicketPilotDas.lifespan). Same pattern as TicketStatusType.py
-- see that file's docstring for why this exists.
"""
from typing import Dict

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.entity.DbModels import OrderStatusType

_ORDER_STATUS_ID_BY_NAME: Dict[str, int] = {}
_ORDER_STATUS_NAME_BY_ID: Dict[int, str] = {}


class OrderStatusTypeNotFoundError(Exception):
    """Raised when a name/id is asked for that was never seeded into
    OrderStatusType -- this means the seed data and CommonEnums.OrderStatus
    are out of sync, which is a setup bug, not a normal runtime error."""


def load_order_status_cache(db: Session) -> None:
    """Reads every row of OrderStatusType once and fills both caches.
    Call this once at app startup, after the tables exist."""
    _ORDER_STATUS_ID_BY_NAME.clear()
    _ORDER_STATUS_NAME_BY_ID.clear()
    for row in db.query(OrderStatusType).all():
        _ORDER_STATUS_ID_BY_NAME[row.OST_Name] = row.OST_Id
        _ORDER_STATUS_NAME_BY_ID[row.OST_Id] = row.OST_Name


def get_cached_order_status_id_by_name(name: str) -> int:
    try:
        return _ORDER_STATUS_ID_BY_NAME[name]
    except KeyError:
        raise OrderStatusTypeNotFoundError(
            f"OrderStatusType '{name}' is not in the cache -- is it seeded in OrderStatusType and spelled "
            f"exactly like CommonEnums.OrderStatus?"
        )


def get_cached_order_status_name_by_id(status_id: int) -> str:
    try:
        return _ORDER_STATUS_NAME_BY_ID[status_id]
    except KeyError:
        raise OrderStatusTypeNotFoundError(f"OrderStatusType id {status_id} is not in the cache.")
