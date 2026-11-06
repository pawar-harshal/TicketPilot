"""
close_ticket -- the ONLY way a ticket ever becomes "resolved" now.

Previously, run_investigation() auto-resolved a ticket the instant the LLM
gave any plain-text reply. That skipped the normal support pattern of
"here's your answer -- anything else?" and risked closing a ticket the
customer wasn't actually done with. Now a plain-text reply just moves the
ticket to AWAITING_CUSTOMER (see AgentOrchestrator.run_investigation) and
the agent is expected to ask if there's anything else. This tool is what
the agent calls once the customer has explicitly confirmed they're
satisfied / have nothing further -- only then does the ticket actually
close, with a real T_ResolvedDate.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_id_by_name
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Ticket, TicketMessage
from ticketpilot_das.utils.CommonEnums import TicketMessageSender, TicketStatus, ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.CloseTicketTool")

TOOL_NAME = ToolName.CLOSE_TICKET.value

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Close this ticket as resolved. Call this ONLY after the customer "
                       "has explicitly confirmed they're satisfied and have nothing further "
                       "-- e.g. they said 'no that's all', 'thanks, that's it', or similar. "
                       "Do not call this just because your own reply sounds final; wait for "
                       "the customer's confirmation.",
        "parameters": {
            "type": "object",
            "properties": {
                "closing_message": {
                    "type": "string",
                    "description": "A short, friendly closing message shown directly to the "
                                    "customer (e.g. 'Glad I could help! Feel free to reach out "
                                    "again if anything else comes up.').",
                },
            },
            "required": ["closing_message"],
        },
    },
}


def run(db: Session, ticket: Ticket, closing_message: str) -> dict:
    try:
        log.info("close_ticket called for ticket %s.", ticket.T_Id)
        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.RESOLVED.value)
        ticket.T_ResolvedDate = datetime.now()
        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.AGENT.value),
            TM_Message=closing_message,
        ))
        db.commit()
        return {"status": "resolved"}
    except Exception as exc:
        log.error("Unexpected error in close_ticket for ticket %s: %s", ticket.T_Id, exc)
        db.rollback()
        return {"error": "Could not close this ticket right now."}
