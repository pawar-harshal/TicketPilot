"""
SQLAlchemy models owned by ticket_management: Customer, Order, Ticket,
TicketMessage, KnowledgeBaseArticle, and the master/lookup tables
TicketStatusType, OrderStatusType, MessageSenderType and Currency.
Column names follow the company convention of <TablePrefix>_<Field> (see
TicketPilot DB Design workbook / TicketPilot_structure.sql).

MASTER TABLES: TicketStatusType, OrderStatusType and MessageSenderType are
small, fixed lookup tables (a handful of rows each, e.g. "investigating",
"resolved", ...) referenced by int FK from Ticket/Order/TicketMessage,
instead of storing the status/sender as a raw string. Currency is the same
idea for money amounts. Resolving a *_Id from a name (or back) goes
through that table's cache module in db_operations/ -- see
ticket_management/db_operations/TicketStatusType.py and friends -- never
a raw query scattered through business logic.

Note: Approval/ApprovalStatusType/ApprovalActionType (approval_engine) and
User (auth) are defined in their own modules' DbModels.py, but all share
the same Base/metadata via ticketpilot_das.utils.Database, so create_all()
picks up every table.
"""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ticketpilot_das.utils.Database import Base


class Currency(Base):
    """Master table: which currencies TicketPilot can record amounts in.
    Only INR is seeded today -- see CommonEnums.CurrencyCode."""
    __tablename__ = "Currency"

    CUR_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    CUR_Code = Column(String(10), nullable=False, unique=True)
    CUR_Name = Column(String(50), nullable=False)
    CUR_Symbol = Column(String(5), nullable=False)


class MessageSenderType(Base):
    """Master table: who can write a TicketMessage. See
    CommonEnums.TicketMessageSender for the matching name strings."""
    __tablename__ = "MessageSenderType"

    MST_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    MST_Name = Column(String(20), nullable=False, unique=True)


class TicketStatusType(Base):
    """Master table: the fixed set of statuses a Ticket can be in. See
    CommonEnums.TicketStatus for the matching name strings."""
    __tablename__ = "TicketStatusType"

    TST_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    TST_Name = Column(String(30), nullable=False, unique=True)


class OrderStatusType(Base):
    """Master table: the fixed set of statuses an Order can be in. See
    CommonEnums.OrderStatus for the matching name strings."""
    __tablename__ = "OrderStatusType"

    OST_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    OST_Name = Column(String(30), nullable=False, unique=True)


class Customer(Base):
    __tablename__ = "Customer"

    C_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    C_Name = Column(String(255), nullable=False)
    C_Email = Column(String(255), nullable=False, unique=True)
    C_Phone = Column(String(20), nullable=False)
    # Nullable because this column was added after Customer already
    # existed (see the ALTER TABLE in the auth rollout notes) -- a row
    # with no hash simply can't log in. Every seeded demo customer has
    # one backfilled.
    C_PasswordHash = Column(String(255), nullable=True)
    C_CreatedDate = Column(DateTime, nullable=False, server_default=func.now())

    orders = relationship("Order", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")


class Order(Base):
    __tablename__ = "Order"

    O_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    C_Id = Column(BigInteger, ForeignKey("Customer.C_Id"), nullable=False)
    O_Items = Column(JSON, nullable=False)
    CUR_Id = Column(BigInteger, ForeignKey("Currency.CUR_Id"), nullable=False)
    O_TotalAmount = Column(Numeric(10, 2), nullable=False)
    O_StatusId = Column(BigInteger, ForeignKey("OrderStatusType.OST_Id"), nullable=False)
    O_OutForDeliveryDate = Column(DateTime, nullable=True)
    O_DeliveryEta = Column(DateTime, nullable=True)
    O_DeliveredDate = Column(DateTime, nullable=True)
    # Demo-only, optional tag: set directly in the DB (not by any code
    # path anymore) to borrow one of DemoScenario.SCENARIO_TEMPLATES'
    # relative-timing offsets for this order. When set,
    # DemoScenario.ensure_order_fresh() recomputes O_OutForDeliveryDate/
    # O_DeliveryEta/O_DeliveredDate relative to "now" every time this
    # order is read, so a hosted demo never shows an absurdly-overdue
    # "5000 minutes late" order. NULL for every other order (a real one,
    # or a demo order whose timing we're fine keeping static). Never
    # touches O_StatusId/O_Items/O_TotalAmount -- those are always the
    # database's own fixed truth, and each customer has exactly ONE
    # order (no more per-scenario duplicate orders per customer).
    O_ScenarioKey = Column(String(50), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")
    currency = relationship("Currency")
    status_type = relationship("OrderStatusType")


class Ticket(Base):
    __tablename__ = "Ticket"

    T_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    C_Id = Column(BigInteger, ForeignKey("Customer.C_Id"), nullable=False)
    O_Id = Column(BigInteger, ForeignKey("Order.O_Id"), nullable=False)
    T_StatusId = Column(BigInteger, ForeignKey("TicketStatusType.TST_Id"), nullable=False)
    T_InvestigationTrail = Column(JSON, nullable=True)
    T_CreatedDate = Column(DateTime, nullable=False, server_default=func.now())
    T_ResolvedDate = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="tickets")
    order = relationship("Order", back_populates="tickets")
    status_type = relationship("TicketStatusType")
    messages = relationship(
        "TicketMessage", back_populates="ticket", order_by="TicketMessage.TM_CreatedDate"
    )


class TicketMessage(Base):
    __tablename__ = "TicketMessage"

    TM_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    T_Id = Column(BigInteger, ForeignKey("Ticket.T_Id"), nullable=False)
    TM_SenderId = Column(BigInteger, ForeignKey("MessageSenderType.MST_Id"), nullable=False)
    TM_Message = Column(Text, nullable=False)
    TM_CreatedDate = Column(DateTime, nullable=False, server_default=func.now())

    ticket = relationship("Ticket", back_populates="messages")
    sender_type = relationship("MessageSenderType")


class KnowledgeBaseArticle(Base):
    __tablename__ = "KnowledgeBaseArticle"

    KBA_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    KBA_Title = Column(String(255), nullable=False)
    KBA_Content = Column(Text, nullable=False)
    KBA_EmbeddingSynced = Column(Boolean, nullable=False, default=False)
