"""
Shared enums used across ticket_management, approval_engine and auth.

TicketStatus, TicketMessageSender, ApprovalStatus, ApprovalActionType,
OrderStatus and CurrencyCode hold the exact NAME strings seeded into their
matching master/lookup tables (TicketStatusType, MessageSenderType,
ApprovalStatusType, ApprovalActionType, OrderStatusType, Currency). Code
never hardcodes the numeric *_Id of a master-table row -- it looks the id
up by name through that table's cache module in db_operations/ (see
ticket_management/db_operations/TicketStatusType.py and friends), built
once at app startup. These enum values must stay byte-for-byte identical
to the rows actually seeded into the matching table.

LlmRole is a different kind of thing entirely -- it is NOT our own data,
it is the fixed, external vocabulary the LLM chat-completions API itself
requires ("system"/"user"/"assistant"/"tool"). It has no database table
and never will -- it exists only so AgentOrchestrator.build_message_history
doesn't have raw string literals scattered in it.
"""
from enum import Enum


class TicketStatus(str, Enum):
    INVESTIGATING = "investigating"
    # The agent answered and is waiting to hear if the customer needs
    # anything else -- NOT the same as resolved. A ticket only becomes
    # RESOLVED when the agent explicitly calls close_ticket (because the
    # customer confirmed they're satisfied), never just from giving a
    # plain-text reply. See AgentOrchestrator.run_investigation.
    AWAITING_CUSTOMER = "awaiting_customer"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    PENDING_APPROVAL = "pending_approval"


class TicketMessageSender(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalActionType(str, Enum):
    REFUND = "refund"
    CREDIT = "credit"


class UserRole(str, Enum):
    """The closed set of principal roles a JWT's "role" claim can carry.
    SUPPORT_MANAGER backs a row in the User table; CUSTOMER backs a row
    in Customer instead (see auth.db_operations.Auth.get_current_user
    vs get_current_customer) -- they're two different tables, but one
    shared token format and one shared /auth/login endpoint that tries
    User first, then Customer, by email."""
    SUPPORT_MANAGER = "support_manager"
    CUSTOMER = "customer"


class OrderStatus(str, Enum):
    PLACED = "placed"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CurrencyCode(str, Enum):
    """Matches Currency.CUR_Code rows. Only INR is seeded for now -- add
    more here (and in the seed data) if/when TicketPilot needs them."""
    INR = "INR"


class LlmRole(str, Enum):
    """The fixed roles the LLM chat-completions API itself defines. Not
    our data, no database table -- see module docstring above."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolName(str, Enum):
    """The closed set of tool names the agent may call. AgentOrchestrator
    and every tool module reference these instead of hardcoding the
    string literal in more than one place."""
    CHECK_ORDER_STATUS = "check_order_status"
    CHECK_ACCOUNT_HISTORY = "check_account_history"
    SEARCH_KNOWLEDGE_BASE = "search_knowledge_base"
    PROPOSE_ACTION = "propose_action"
    ESCALATE_TICKET = "escalate_ticket"
    CLOSE_TICKET = "close_ticket"
