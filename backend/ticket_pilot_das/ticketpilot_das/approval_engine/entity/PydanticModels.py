from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApprovalOut(BaseModel):
    approval_id: int
    ticket_id: int
    action_type: str
    amount: float
    currency: str
    reason: str
    status: str
    approver_id: Optional[int] = None
    decided_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class RejectActionRequest(BaseModel):
    reason: Optional[str] = None


class ApproveActionRequest(BaseModel):
    # Only actually required (enforced server-side in
    # approval_engine.db_operations.Approval.approve_action) when the
    # underlying order is already marked "delivered" -- that's the case
    # where the KB policy calls for courier confirmation before a
    # refund/credit goes through (see ticket_management.tools.ApprovalTool's
    # courier_check_note). Defaults to False so an approval that doesn't
    # need it still works with no body at all.
    courier_confirmed: bool = False
