"""
SQLAlchemy models owned by approval_engine: Approval, and the master/lookup
tables ApprovalStatusType and ApprovalActionType.

MASTER TABLES: ApprovalStatusType and ApprovalActionType are small, fixed
lookup tables (e.g. "pending"/"approved"/"rejected", "refund"/"credit")
referenced by int FK from Approval, instead of storing the status/action
as a raw string. Resolving a *_Id from a name (or back) goes through that
table's cache module in db_operations/ -- see
approval_engine/db_operations/ApprovalStatusType.py and friends -- never
a raw query scattered through business logic.

AuditLog has been dropped (unused -- Approval already records who decided
it and when via AP_ApproverId/AP_DecidedDate).
"""
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text

from ticketpilot_das.utils.Database import Base


class ApprovalStatusType(Base):
    """Master table: the fixed set of statuses an Approval can be in. See
    CommonEnums.ApprovalStatus for the matching name strings."""
    __tablename__ = "ApprovalStatusType"

    APST_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    APST_Name = Column(String(20), nullable=False, unique=True)


class ApprovalActionType(Base):
    """Master table: the fixed set of actions an Approval can request. See
    CommonEnums.ApprovalActionType for the matching name strings."""
    __tablename__ = "ApprovalActionType"

    APAT_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    APAT_Name = Column(String(20), nullable=False, unique=True)


class Approval(Base):
    __tablename__ = "Approval"

    AP_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    T_Id = Column(BigInteger, ForeignKey("Ticket.T_Id"), nullable=False)
    APAT_Id = Column(BigInteger, ForeignKey("ApprovalActionType.APAT_Id"), nullable=False)
    AP_Amount = Column(Numeric(10, 2), nullable=False)
    CUR_Id = Column(BigInteger, ForeignKey("Currency.CUR_Id"), nullable=False)
    AP_Reason = Column(Text, nullable=False)
    APST_Id = Column(BigInteger, ForeignKey("ApprovalStatusType.APST_Id"), nullable=False)
    AP_ApproverId = Column(BigInteger, ForeignKey("User.U_Id"), nullable=True)
    AP_DecidedDate = Column(DateTime, nullable=True)
