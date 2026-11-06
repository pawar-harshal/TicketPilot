"""
check_account_history -- lets the agent see the customer's recent order
history (e.g. to notice "this is the third late delivery this month").

GOVERNANCE: scoped the same way as OrderLookupTool -- always keyed off the
ticket's own C_Id, never off anything the model supplies.
"""
from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.db_operations.OrderStatusType import get_cached_order_status_name_by_id
from ticketpilot_das.ticket_management.entity.DbModels import Order, Ticket
from ticketpilot_das.utils.CommonEnums import ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.AccountLookupTool")

TOOL_NAME = ToolName.CHECK_ACCOUNT_HISTORY.value

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Look up this ticket's customer's recent order history (most recent 10 orders).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}


def run(db: Session, ticket: Ticket) -> dict:
    try:
        log.debug("check_account_history called for ticket %s (customer %s)", ticket.T_Id, ticket.C_Id)
        orders = (
            db.query(Order)
            .filter(Order.C_Id == ticket.C_Id)
            .order_by(Order.O_Id.desc())
            .limit(10)
            .all()
        )
        return {
            "customer_id": ticket.C_Id,
            "recent_orders": [
                {
                    "order_id": o.O_Id,
                    "status": get_cached_order_status_name_by_id(o.O_StatusId),
                    "total_amount": str(o.O_TotalAmount),
                }
                for o in orders
            ],
        }
    except Exception as exc:
        log.error("Unexpected error in check_account_history for ticket %s: %s", ticket.T_Id, exc)
        return {"error": "Could not look up account history right now."}
