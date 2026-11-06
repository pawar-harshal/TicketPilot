"""Request/response schemas for the ticket_management endpoints."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SubmitTicketRequest(BaseModel):
    # customer_id is deliberately NOT a field here anymore -- it used to
    # be, which meant any caller could submit a ticket as any customer
    # just by putting a different id in the request body. Now that
    # customers log in, the caller's identity comes from their JWT (see
    # get_current_customer), never from anything in this payload.
    order_id: Optional[int] = Field(
        None, description="Order this ticket is about. Optional -- if omitted, the "
                          "customer's own most recent order is used (every demo customer "
                          "has exactly one). Provided mainly for a customer with more "
                          "than one order to pick which one."
    )
    # NOTE: there used to be a scenario_id field here that told the backend
    # to create-or-refresh a DEDICATED demo order per (customer, scenario)
    # and raise the ticket against THAT instead. Removed: it meant a
    # customer could end up with several different orders, and whichever
    # one the home-page status panel shows (their single most recent
    # order) could be a different one than whatever scenario card they'd
    # just clicked -- the chat and the dashboard would disagree about
    # what "the order" even was. Now every demo customer has exactly ONE
    # order, period, and a scenario card is just canned message text
    # (see frontend scenarios.js) -- it never affects which order is
    # used. See ticket_management.db_operations.DemoScenario for how
    # that one order's TIMING (not status) stays fresh instead.
    message: str = Field(..., min_length=1, description="The customer's free-text complaint/question.")


class ReopenTicketRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Why the customer is reopening / the new issue.")


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The customer's next message in an existing, still-open ticket.")


class TicketMessageOut(BaseModel):
    sender: str
    message: str
    created_date: datetime

    class Config:
        from_attributes = True


class TicketOut(BaseModel):
    ticket_id: int
    customer_id: int
    order_id: int
    status: str
    created_date: datetime
    resolved_date: Optional[datetime] = None
    messages: List[TicketMessageOut] = []

    # Added so a support manager (reviewing an approval or an escalated
    # ticket) sees the SAME real facts the agent itself saw, instead of
    # having to take the agent's word for it or re-derive them by hand:
    #
    # `order` -- a snapshot of this ticket's order (items, total, real
    # delivery status/lateness), straight from OrderLookupTool.run --
    # the exact same function check_order_status calls, so this is
    # never a second, possibly-drifted copy of that logic.
    #
    # `investigation_trail` -- every tool call the agent made while
    # working this ticket (Ticket.T_InvestigationTrail), including which
    # knowledge-base article(s) search_knowledge_base matched -- this is
    # what lets the UI show "which policy the agent used" as a real,
    # traceable fact instead of free text someone has to re-type.
    order: Optional[Dict[str, Any]] = None
    investigation_trail: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class MyOrderStatusOut(BaseModel):
    # `order` is the same snapshot shape TicketOut.order uses (items,
    # total, status, is_late/minutes_late) -- straight from
    # OrderLookupTool.get_latest_order_snapshot, so this is never a
    # second, possibly-drifted copy of that logic. None means the
    # customer has no orders at all yet (a normal state, not an error).
    order: Optional[Dict[str, Any]] = None


class TicketSummaryOut(BaseModel):
    ticket_id: int
    customer_id: int
    order_id: int
    status: str
    created_date: datetime
    last_message: Optional[str] = None

    class Config:
        from_attributes = True
