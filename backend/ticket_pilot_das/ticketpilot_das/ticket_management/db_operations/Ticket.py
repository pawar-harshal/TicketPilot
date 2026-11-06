"""
Business logic for ticket_management's ticket lifecycle: submit, reopen, read.

This is the ONLY place that writes to the Ticket/TicketMessage tables.
It is also the only place that kicks off the AgentOrchestrator's
tool-calling investigation loop, and it is responsible for persisting
whatever the agent decided back onto the ticket.
"""
from typing import List

from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.AgentOrchestrator import run_investigation
from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_id_by_name
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Customer, Order, Ticket, TicketMessage
from ticketpilot_das.utils.CommonEnums import TicketMessageSender, TicketStatus
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.db_operations.Ticket")


def submit_ticket(
    db: Session, customer_id: int, order_id: int = None, message: str = ""
) -> Ticket:
    """Create a brand-new ticket, record the customer's opening message, and
    run the agent's investigation loop synchronously before returning.

    customer_id comes from the caller's own JWT (get_current_customer) --
    never from a request body field -- so there's no way to submit a
    ticket "as" a different customer.

    order_id is optional: when omitted, we use that customer's own most
    recent order (every demo customer has exactly one, so this is
    unambiguous; a customer with several real orders would pass order_id
    explicitly to pick). This is also exactly the order the customer's
    home-page status panel shows (see OrderLookupTool.get_latest_order_
    snapshot) -- a "Get Help" scenario card never picks a different one;
    it only supplies canned message text (see frontend scenarios.js), so
    the chat and the dashboard always agree on which order they're both
    talking about."""
    try:
        customer = db.get(Customer, customer_id)
        if customer is None:
            log.warning("submit_ticket: no such customer %s.", customer_id)
            raise ValueError(f"No such customer: {customer_id}")

        if order_id is None:
            order = (
                db.query(Order)
                .filter(Order.C_Id == customer_id)
                .order_by(Order.O_Id.desc())
                .first()
            )
            if order is None:
                log.warning("submit_ticket: customer %s has no orders at all.", customer_id)
                raise ValueError(f"Customer {customer_id} has no orders to raise a ticket about.")
            order_id = order.O_Id
        else:
            order = db.get(Order, order_id)
            if order is None or order.C_Id != customer_id:
                # Scope check: a customer may only raise a ticket against their OWN order.
                log.warning("submit_ticket: order %s does not belong to customer %s.", order_id, customer_id)
                raise ValueError(f"Order {order_id} does not belong to customer {customer_id}")

        ticket = Ticket(
            C_Id=customer_id,
            O_Id=order_id,
            T_StatusId=get_cached_ticket_status_id_by_name(TicketStatus.INVESTIGATING.value),
        )
        db.add(ticket)
        db.flush()  # assigns T_Id without committing yet

        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.CUSTOMER.value),
            TM_Message=message,
        ))
        db.commit()
        db.refresh(ticket)

        log.info("Ticket %s submitted for customer %s, order %s", ticket.T_Id, customer_id, order_id)

        # Synchronous investigation: this call blocks until the agent's full
        # tool-calling loop finishes, then we persist whatever it decided.
        run_investigation(db, ticket.T_Id)

        db.refresh(ticket)
        return ticket
    except ValueError:
        db.rollback()
        raise
    except Exception as exc:
        log.error("Unexpected error submitting ticket for customer %s, order %s: %s", customer_id, order_id, exc)
        db.rollback()
        raise


def reopen_ticket(db: Session, ticket_id: int, message: str) -> Ticket:
    """Customer is unsatisfied with a resolved ticket -- put it back into
    investigation instead of making them file a brand-new one."""
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            log.warning("reopen_ticket: no such ticket %s.", ticket_id)
            raise ValueError(f"No such ticket: {ticket_id}")

        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.INVESTIGATING.value)
        ticket.T_ResolvedDate = None

        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.CUSTOMER.value),
            TM_Message=message,
        ))
        db.commit()
        db.refresh(ticket)

        log.info("Ticket %s reopened", ticket_id)

        run_investigation(db, ticket.T_Id)

        db.refresh(ticket)
        return ticket
    except ValueError:
        db.rollback()
        raise
    except Exception as exc:
        log.error("Unexpected error reopening ticket %s: %s", ticket_id, exc)
        db.rollback()
        raise


def send_message(db: Session, ticket_id: int, message: str) -> Ticket:
    """Appends a new customer message to an EXISTING, still-open ticket --
    this is what lets a demo/real conversation feel like one continuous
    chat thread instead of a brand-new ticket per message (that's what
    submit_ticket always does). Distinct from reopen_ticket, which is
    specifically for reviving an already-CLOSED ticket.

    Behavior depends on the ticket's current status:
      - investigating / awaiting_customer: this is exactly what the agent
        was waiting for -- append the message, flip back to investigating,
        and re-run the agent loop.
      - escalated / pending_approval: a human already owns this ticket (or
        a decision is already in flight), so we just record the message
        for whoever picks it up -- we do NOT let the agent jump back in
        and reply, to avoid racing a human's in-progress action.
      - resolved: this ticket is closed. Don't silently reopen it here --
        tell the caller to use reopen_ticket instead, which is the
        explicit, intentional way to revive a closed ticket.
    """
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            log.warning("send_message: no such ticket %s.", ticket_id)
            raise ValueError(f"No such ticket: {ticket_id}")

        resolved_id = get_cached_ticket_status_id_by_name(TicketStatus.RESOLVED.value)
        escalated_id = get_cached_ticket_status_id_by_name(TicketStatus.ESCALATED.value)
        pending_approval_id = get_cached_ticket_status_id_by_name(TicketStatus.PENDING_APPROVAL.value)

        if ticket.T_StatusId == resolved_id:
            log.warning("send_message: ticket %s is already resolved.", ticket_id)
            raise ValueError(f"Ticket {ticket_id} is already resolved -- use reopenTicket instead.")

        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.CUSTOMER.value),
            TM_Message=message,
        ))

        if ticket.T_StatusId in (escalated_id, pending_approval_id):
            # A human already owns this -- just record the message, don't
            # let the agent respond.
            db.commit()
            db.refresh(ticket)
            log.info("Ticket %s: message recorded while %s -- human owns this, agent not re-run.",
                      ticket_id, "escalated" if ticket.T_StatusId == escalated_id else "pending_approval")
            return ticket

        # investigating / awaiting_customer -- the agent should pick this back up.
        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.INVESTIGATING.value)
        db.commit()
        db.refresh(ticket)

        log.info("Ticket %s: new message added, re-running agent.", ticket_id)
        run_investigation(db, ticket.T_Id)

        db.refresh(ticket)
        return ticket
    except ValueError:
        db.rollback()
        raise
    except Exception as exc:
        log.error("Unexpected error sending message to ticket %s: %s", ticket_id, exc)
        db.rollback()
        raise


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    try:
        ticket = db.get(Ticket, ticket_id)
        if ticket is None:
            log.debug("get_ticket: no such ticket %s.", ticket_id)
            raise ValueError(f"No such ticket: {ticket_id}")
        return ticket
    except ValueError:
        raise
    except Exception as exc:
        log.error("Unexpected error fetching ticket %s: %s", ticket_id, exc)
        raise


def get_tickets(db: Session, customer_id: int = None, status: str = None) -> List[Ticket]:
    try:
        query = db.query(Ticket)
        if customer_id is not None:
            query = query.filter(Ticket.C_Id == customer_id)
        if status is not None:
            # Raises TicketStatusTypeNotFoundError (caught below, surfaced as a 400 by
            # the route) if the caller passed a status name that was never seeded --
            # e.g. a typo like "Escalated" instead of "escalated".
            query = query.filter(Ticket.T_StatusId == get_cached_ticket_status_id_by_name(status))
        return query.order_by(Ticket.T_CreatedDate.desc()).all()
    except Exception as exc:
        log.error("Unexpected error listing tickets (customer_id=%s, status=%s): %s", customer_id, status, exc)
        raise
