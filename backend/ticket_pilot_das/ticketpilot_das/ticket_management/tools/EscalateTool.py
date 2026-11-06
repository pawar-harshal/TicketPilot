"""
escalate_ticket -- the agent's way of saying "a human needs to take this
over," for anything outside what it can resolve or propose (e.g. a
complaint that isn't about an order at all, or something it isn't
confident about).
"""
from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_id_by_name
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Ticket, TicketMessage
from ticketpilot_das.utils.CommonEnums import TicketMessageSender, TicketStatus, ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.EscalateTool")

TOOL_NAME = ToolName.ESCALATE_TICKET.value

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Hand this ticket off to a human support manager, with a short "
                       "note on why. Use this when the ticket is outside what you can "
                       "resolve directly or propose an action for.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why this needs a human -- this is an INTERNAL note for "
                                    "whoever picks up the ticket, not shown to the customer, "
                                    "so write it for a support manager, not for the customer.",
                },
            },
            "required": ["reason"],
        },
    },
}


def run(db: Session, ticket: Ticket, reason: str) -> dict:
    try:
        log.info("escalate_ticket called for ticket %s: %s", ticket.T_Id, reason)
        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.ESCALATED.value)
        # `reason` is an internal note (written in third person, for whoever picks this
        # up) -- it is NOT customer-facing copy, and already lives in
        # Ticket.T_InvestigationTrail for internal review, so it is deliberately not
        # repeated here. The customer only ever sees this fixed, direct message.
        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.SYSTEM.value),
            TM_Message=(
                "This needs a closer look than I can give it on my own, so I've passed it "
                "along to a member of our support team -- they'll follow up with you "
                "directly to help resolve this. Thank you for your patience."
            ),
        ))
        db.commit()
        return {"status": "escalated"}
    except Exception as exc:
        log.error("Unexpected error in escalate_ticket for ticket %s: %s", ticket.T_Id, exc)
        db.rollback()
        return {"error": "Could not escalate this ticket right now."}
