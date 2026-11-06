"""FastAPI routes for ticket_management.

Every route here now requires SOME logged-in principal -- a customer
(their own tickets/actions only) or a support manager (read-only access
to everyone's). There is no more fully-public path: that used to mean
anyone could submit a ticket "as" any customer_id, read any ticket_id, or
list every ticket's status/last_message with no login at all.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ticketpilot_das.auth.db_operations.Auth import get_current_customer, get_current_user, optional_oauth2_scheme
from ticketpilot_das.auth.entity.DbModels import User
from ticketpilot_das.ticket_management.db_operations import Ticket as ticket_ops
from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_name_by_id
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import (
    TicketStatusTypeNotFoundError,
    get_cached_ticket_status_name_by_id,
)
from ticketpilot_das.ticket_management.entity.DbModels import Customer
from ticketpilot_das.ticket_management.entity.PydanticModels import (
    MyOrderStatusOut,
    ReopenTicketRequest,
    SendMessageRequest,
    SubmitTicketRequest,
    TicketOut,
    TicketSummaryOut,
)
from ticketpilot_das.ticket_management.tools import OrderLookupTool
from ticketpilot_das.utils.Database import get_db
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.routes.Ticket")

router = APIRouter(prefix="/ticketmanagement", tags=["ticket_management"])


@router.post("/submitTicket", response_model=TicketOut)
def submit_ticket(
    payload: SubmitTicketRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Function: submitTicket
    Description: Creates a new support ticket and runs the agent's full
        investigation loop SYNCHRONOUSLY before returning -- the HTTP
        request stays open until the agent has a reply, an escalation,
        or a proposed action.
    Inputs: order_id (optional path to a specific order), message. The
        customer is whoever's JWT this is -- there is no customer_id
        field in the body anymore (see SubmitTicketRequest).
    Outputs: the ticket, including the agent's reply (if resolved) in
        its message history.
    Happy Flow: order belongs to the customer (or is omitted and their
        own most recent order is used) -> ticket + first TicketMessage
        created -> AgentOrchestrator runs -> ticket returned with its
        final status.
    Error Flow: order_id given but doesn't belong to this customer, or
        the customer has no orders at all -> 400. No/invalid customer
        JWT -> 401.
    """
    try:
        log.info(
            "POST submitTicket -- customer_id=%s order_id=%s",
            current_customer.C_Id, payload.order_id,
        )
        ticket = ticket_ops.submit_ticket(
            db, current_customer.C_Id, payload.order_id, payload.message
        )
        return to_ticket_out(ticket, db)
    except ValueError as exc:
        log.warning("submitTicket rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in submitTicket: %s", exc)
        raise HTTPException(status_code=500, detail="Could not submit ticket.")


@router.get("/myOrderStatus", response_model=MyOrderStatusOut)
def get_my_order_status(
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Function: myOrderStatus
    Description: The logged-in customer's own current order, OUTSIDE of
        any ticket/chat context -- backs the live order-status panel on
        the customer's home page (SubmitTicket.jsx), so "where's my
        order" is answered without having to start a conversation with
        the support agent just to ask that.
    Inputs: none -- customer comes from the JWT.
    Outputs: { order: <snapshot> | null }. null means this customer has
        no orders at all (a normal state for a brand-new customer).
    Happy Flow: customer's most recent order (same default
        submit_ticket already uses) -> its real status/lateness via
        OrderLookupTool.get_latest_order_snapshot.
    Error Flow: no/invalid customer JWT -> 401 (via get_current_customer).
    """
    try:
        snapshot = OrderLookupTool.get_latest_order_snapshot(db, current_customer.C_Id)
        if snapshot is not None and "error" in snapshot:
            raise HTTPException(status_code=500, detail="Could not load order status.")
        return MyOrderStatusOut(order=snapshot)
    except HTTPException:
        raise
    except Exception as exc:
        log.error("Unexpected error in myOrderStatus for customer %s: %s", current_customer.C_Id, exc)
        raise HTTPException(status_code=500, detail="Could not load order status.")


@router.post("/reopenTicket/{ticket_id}", response_model=TicketOut)
def reopen_ticket(
    ticket_id: int,
    payload: ReopenTicketRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Function: reopenTicket
    Description: Lets a customer reopen a ticket that is already
        resolved, instead of filing a brand-new one -- appends their
        new message to the SAME conversation and re-runs the
        investigation loop with full prior context.
    Inputs: ticket_id (path), message.
    Outputs: the ticket, updated.
    Happy Flow: ticket exists AND belongs to this customer -> status
        reset to investigating, resolved_date cleared -> message
        appended -> agent re-runs.
    Error Flow: ticket_id doesn't exist -> 404. Ticket belongs to a
        different customer -> 403 (this used to be wide open -- anyone
        could reopen/post into ANY ticket_id with no ownership check
        at all).
    """
    try:
        log.info("POST reopenTicket -- ticket_id=%s customer_id=%s", ticket_id, current_customer.C_Id)
        _assert_owns_ticket(db, ticket_id, current_customer.C_Id)
        ticket = ticket_ops.reopen_ticket(db, ticket_id, payload.message)
        return to_ticket_out(ticket, db)
    except PermissionError as exc:
        log.warning("reopenTicket rejected -- not this customer's ticket: %s", exc)
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        log.warning("reopenTicket rejected: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in reopenTicket %s: %s", ticket_id, exc)
        raise HTTPException(status_code=500, detail="Could not reopen ticket.")


@router.post("/sendMessage/{ticket_id}", response_model=TicketOut)
def send_message(
    ticket_id: int,
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    current_customer: Customer = Depends(get_current_customer),
):
    """
    Function: sendMessage
    Description: Appends the customer's next message to an EXISTING,
        still-open ticket and (when appropriate) re-runs the agent --
        this is what turns the API from "one ticket per message" into a
        real back-and-forth conversation thread. Distinct from
        reopenTicket, which is specifically for reviving a ticket that's
        already resolved.
    Inputs: ticket_id (path), message.
    Outputs: the ticket, updated.
    Happy Flow (investigating/awaiting_customer): message appended ->
        agent re-runs -> ticket returned with its new status/reply.
    Happy Flow (escalated/pending_approval): message appended and stored
        for the human handling it, but the agent is NOT re-run.
    Error Flow: ticket_id doesn't exist -> 404. Ticket belongs to a
        different customer -> 403. Ticket is already resolved -> 400
        (use reopenTicket instead).
    """
    try:
        log.info("POST sendMessage -- ticket_id=%s customer_id=%s", ticket_id, current_customer.C_Id)
        _assert_owns_ticket(db, ticket_id, current_customer.C_Id)
        ticket = ticket_ops.send_message(db, ticket_id, payload.message)
        return to_ticket_out(ticket, db)
    except PermissionError as exc:
        log.warning("sendMessage rejected -- not this customer's ticket: %s", exc)
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        log.warning("sendMessage rejected for ticket %s: %s", ticket_id, exc)
        status_code = 404 if "No such ticket" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in sendMessage %s: %s", ticket_id, exc)
        raise HTTPException(status_code=500, detail="Could not send message.")


@router.get("/getTicket/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    token: str = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Function: getTicket
    Description: Fetches one ticket with its full conversation history.
        Open to two different principals: a support manager can view
        ANY ticket (read-only context for approvals/escalations); a
        customer can only view their OWN ticket.
    Inputs: ticket_id (path).
    Outputs: the ticket and its ordered TicketMessage list.
    Happy Flow: a manager JWT -> any ticket returned. A customer JWT
        whose C_Id matches the ticket -> returned.
    Error Flow: ticket_id doesn't exist -> 404. No/invalid JWT -> 401.
        A customer JWT for a DIFFERENT customer's ticket -> 403 (this
        used to be wide open -- any ticket_id was readable by anyone,
        no login at all, which could expose another customer's refund
        amount, complaint text, etc.).
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Login required.")

    try:
        ticket = ticket_ops.get_ticket(db, ticket_id)
    except ValueError as exc:
        log.debug("getTicket miss: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in getTicket %s: %s", ticket_id, exc)
        raise HTTPException(status_code=500, detail="Could not load ticket.")

    manager = _try_get_manager(token, db)
    if manager is not None:
        return to_ticket_out(ticket, db)

    customer = _try_get_customer(token, db)
    if customer is None:
        # Token didn't decode as either kind of valid principal.
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    if customer.C_Id != ticket.C_Id:
        log.warning("getTicket rejected -- customer %s tried to view ticket %s owned by customer %s.",
                     customer.C_Id, ticket_id, ticket.C_Id)
        raise HTTPException(status_code=403, detail="This isn't your ticket.")

    return to_ticket_out(ticket, db)


@router.get("/getTickets", response_model=list[TicketSummaryOut])
def get_tickets(
    status: str = Query(
        None,
        description="Filter to one status, e.g. 'escalated', 'pending_approval', "
                    "'investigating', 'resolved'. Used by the support manager's queue "
                    "screen to pull just the tickets that need a human right now.",
    ),
    token: str = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Function: getTickets
    Description: Lists tickets, most recent first. A support manager
        sees across EVERY customer (optionally filtered by status) --
        that's the "All Tickets" / "Escalated Tickets" panels. A
        customer sees only their OWN tickets -- there is no customer_id
        query param anymore; it's derived from the JWT, not asked for.
    Inputs: status (optional query filter).
    Outputs: a list of ticket summaries.
    Happy Flow: returns tickets ordered by created_date desc, scoped to
        whichever principal is logged in.
    Error Flow: an unrecognized status name -> 400. No results -> an
        empty list is a valid result, not an error. No/invalid JWT -> 401.
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Login required to list tickets.")

    manager = _try_get_manager(token, db)
    if manager is not None:
        customer_id = None  # across everyone
    else:
        customer = _try_get_customer(token, db)
        if customer is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        customer_id = customer.C_Id

    try:
        tickets = ticket_ops.get_tickets(db, customer_id, status)
        return [
            TicketSummaryOut(
                ticket_id=t.T_Id,
                customer_id=t.C_Id,
                order_id=t.O_Id,
                status=get_cached_ticket_status_name_by_id(t.T_StatusId),
                created_date=t.T_CreatedDate,
                last_message=t.messages[-1].TM_Message if t.messages else None,
            )
            for t in tickets
        ]
    except TicketStatusTypeNotFoundError as exc:
        log.warning("getTickets rejected -- bad status filter: %s", exc)
        raise HTTPException(status_code=400, detail=f"Unrecognized status '{status}'.")
    except Exception as exc:
        log.error("Unexpected error in getTickets (customer_id=%s, status=%s): %s", customer_id, status, exc)
        raise HTTPException(status_code=500, detail="Could not list tickets.")


def _assert_owns_ticket(db: Session, ticket_id: int, customer_id: int) -> None:
    """Shared ownership check for reopenTicket/sendMessage -- raises
    ValueError (-> 404) if the ticket doesn't exist, PermissionError
    (-> 403) if it exists but belongs to someone else."""
    ticket = ticket_ops.get_ticket(db, ticket_id)  # raises ValueError if missing
    if ticket.C_Id != customer_id:
        raise PermissionError("This isn't your ticket.")


def _try_get_manager(token: str, db: Session) -> User | None:
    """get_current_user as a plain lookup instead of a FastAPI Depends --
    returns None (instead of raising) when the token isn't a valid
    manager token, so the caller can fall through and try the customer
    path instead."""
    try:
        return get_current_user(token=token, db=db)
    except HTTPException:
        return None


def _try_get_customer(token: str, db: Session) -> Customer | None:
    try:
        return get_current_customer(token=token, db=db)
    except HTTPException:
        return None


def to_ticket_out(ticket, db: Session) -> TicketOut:
    # Reuses OrderLookupTool.run -- the EXACT same function
    # check_order_status calls -- so whatever the manager (or the
    # customer, via their own ticket) sees here is guaranteed to be the
    # same real facts the agent itself saw, never a second, possibly
    # drifted copy of the lateness/total/items logic. On the rare chance
    # this returns an {"error": ...} (should only happen if the order
    # record itself is somehow gone), `order` is just omitted rather
    # than failing the whole response.
    order_snapshot = OrderLookupTool.run(db, ticket)
    order_out = None if "error" in order_snapshot else order_snapshot

    return TicketOut(
        ticket_id=ticket.T_Id,
        customer_id=ticket.C_Id,
        order_id=ticket.O_Id,
        status=get_cached_ticket_status_name_by_id(ticket.T_StatusId),
        created_date=ticket.T_CreatedDate,
        resolved_date=ticket.T_ResolvedDate,
        messages=[
            {
                "sender": get_cached_message_sender_name_by_id(m.TM_SenderId),
                "message": m.TM_Message,
                "created_date": m.TM_CreatedDate,
            }
            for m in ticket.messages
        ],
        order=order_out,
        investigation_trail=ticket.T_InvestigationTrail or [],
    )
