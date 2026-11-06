from datetime import datetime

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.db_operations.Currency import get_cached_currency_code_by_id
from ticketpilot_das.ticket_management.db_operations.DemoScenario import ensure_order_fresh
from ticketpilot_das.ticket_management.db_operations.OrderStatusType import get_cached_order_status_name_by_id
from ticketpilot_das.ticket_management.entity.DbModels import Order, Ticket
from ticketpilot_das.utils.CommonEnums import ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.OrderLookupTool")

TOOL_NAME = ToolName.CHECK_ORDER_STATUS.value

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Look up the delivery status of the order this ticket is about, "
                       "including whether it is currently overdue and by how many minutes.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def build_order_snapshot(order: Order) -> dict:
    """The actual lateness/total/items computation, factored out of run()
    so it can also be reused by get_latest_order_snapshot() below --
    anything that needs "the real facts about this Order" (the agent via
    check_order_status, a manager's approval card via getTicket, or the
    customer's own home-page status panel via getMyOrderStatus) goes
    through this ONE function rather than three drifting copies of the
    same is_late/minutes_late math."""
    now = datetime.now()
    is_late = False
    minutes_late = 0
    if order.O_DeliveryEta and order.O_DeliveredDate is None:
        if now > order.O_DeliveryEta:
            is_late = True
            minutes_late = int((now - order.O_DeliveryEta).total_seconds() // 60)

    return {
        "order_id": order.O_Id,
        "status": get_cached_order_status_name_by_id(order.O_StatusId),
        "items": order.O_Items,
        "total_amount": str(order.O_TotalAmount),
        "currency": get_cached_currency_code_by_id(order.CUR_Id),
        "delivery_eta": order.O_DeliveryEta.isoformat() if order.O_DeliveryEta else None,
        "out_for_delivery_date": order.O_OutForDeliveryDate.isoformat() if order.O_OutForDeliveryDate else None,
        "delivered_date": order.O_DeliveredDate.isoformat() if order.O_DeliveredDate else None,
        "is_late": is_late,
        "minutes_late": minutes_late,
    }


def run(db: Session, ticket: Ticket) -> dict:
    try:
        log.debug("check_order_status called for ticket %s (order %s)", ticket.T_Id, ticket.O_Id)
        order = db.get(Order, ticket.O_Id)
        if order is None or order.C_Id != ticket.C_Id:
            log.warning("Order %s not found/mismatched for ticket %s -- scope check failed.", ticket.O_Id, ticket.T_Id)
            return {"error": "Order not found for this ticket's customer."}

        # Demo-only: if this order is tagged with O_ScenarioKey, keep its
        # timing fresh relative to right now before computing lateness --
        # see DemoScenario.ensure_order_fresh. No-op for a real order.
        ensure_order_fresh(db, order)
        return build_order_snapshot(order)
    except Exception as exc:
        log.error("Unexpected error in check_order_status for ticket %s: %s", ticket.T_Id, exc)
        return {"error": "Could not look up order status right now."}


def get_latest_order_snapshot(db: Session, customer_id: int) -> dict | None:
    """Same real facts as run(), but scoped to a customer rather than a
    ticket -- for the logged-in home page's order-status panel, which
    shows "where's my order" outside of any support conversation. Picks
    the customer's single most recent Order (highest O_Id), same default
    ticket_management.db_operations.Ticket.submit_ticket already uses
    when no order_id is given. Returns None (not an error dict) when the
    customer has no orders at all -- a real, normal state for a
    brand-new customer, not a failure."""
    try:
        order = (
            db.query(Order)
            .filter(Order.C_Id == customer_id)
            .order_by(Order.O_Id.desc())
            .first()
        )
        if order is None:
            return None
        ensure_order_fresh(db, order)
        return build_order_snapshot(order)
    except Exception as exc:
        log.error("Unexpected error in get_latest_order_snapshot for customer %s: %s", customer_id, exc)
        return {"error": "Could not look up order status right now."}