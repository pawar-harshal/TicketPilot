"""
Business logic for approval_engine: creating pending approvals, and the
human approve/reject actions that are the ONLY way a refund/credit is
actually executed.

This module owns the Approval table. ticket_management's ApprovalTool
calls create_pending_approval() -- it never calls
approve_action()/reject_action() itself, since those require a real human
(a User row) to have acted.

AuditLog has been dropped -- Approval itself already records who decided
it (AP_ApproverId) and when (AP_DecidedDate), so a separate audit row was
redundant.
"""
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from ticketpilot_das.approval_engine.db_operations.ApprovalActionType import get_cached_approval_action_id_by_name
from ticketpilot_das.approval_engine.db_operations.ApprovalStatusType import (
    get_cached_approval_status_id_by_name,
    get_cached_approval_status_name_by_id,
)
from ticketpilot_das.approval_engine.entity.DbModels import Approval
from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_id_by_name
from ticketpilot_das.ticket_management.db_operations.OrderStatusType import get_cached_order_status_name_by_id
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Order, Ticket, TicketMessage
from ticketpilot_das.utils.CommonEnums import ApprovalStatus, OrderStatus, TicketMessageSender, TicketStatus
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("approval_engine.db_operations.Approval")


def create_pending_approval(
    db: Session, ticket_id: int, action_type: str, amount: float, reason: str, currency_id: int
) -> Approval:
    try:
        log.debug("Creating pending approval for ticket %s: %s %s", ticket_id, action_type, amount)
        approval = Approval(
            T_Id=ticket_id,
            APAT_Id=get_cached_approval_action_id_by_name(action_type),
            AP_Amount=amount,
            CUR_Id=currency_id,
            AP_Reason=reason,
            APST_Id=get_cached_approval_status_id_by_name(ApprovalStatus.PENDING.value),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        log.info("Approval %s created for ticket %s (%s %s)", approval.AP_Id, ticket_id, action_type, amount)
        return approval
    except Exception as exc:
        log.error("Failed to create pending approval for ticket %s: %s", ticket_id, exc)
        db.rollback()
        raise


def get_pending_approvals(db: Session) -> List[Approval]:
    try:
        pending_id = get_cached_approval_status_id_by_name(ApprovalStatus.PENDING.value)
        return (
            db.query(Approval)
            .filter(Approval.APST_Id == pending_id)
            .order_by(Approval.AP_Id.asc())
            .all()
        )
    except Exception as exc:
        log.error("Failed to fetch pending approvals: %s", exc)
        raise


def approve_action(db: Session, approval_id: int, approver_id: int, courier_confirmed: bool = False) -> Approval:
    """The ONLY place a refund/credit is actually executed -- after a real
    human (approver_id, a User row) has signed off.

    courier_confirmed is a hard, server-side-enforced gate (not just a UI
    checkbox a request could skip by calling this endpoint directly):
    when the approval's underlying order is already marked "delivered",
    the KB policy for that situation explicitly calls for confirming
    delivery with the courier first (see
    ticket_management.tools.ApprovalTool's courier_check_note, which
    tells the customer exactly this). approveAction refuses to execute
    until the manager has actually ticked that box for THIS approval --
    same reasoning as every other governance check in this app: a
    written policy/UI hint alone isn't a reliable enough gate for
    something that moves real money."""
    try:
        approval = db.get(Approval, approval_id)
        if approval is None:
            log.warning("approve_action: no such approval %s.", approval_id)
            raise ValueError(f"No such approval: {approval_id}")
        current_status = get_cached_approval_status_name_by_id(approval.APST_Id)
        if current_status != ApprovalStatus.PENDING.value:
            log.warning("approve_action: approval %s is already %s.", approval_id, current_status)
            raise ValueError(f"Approval {approval_id} is already {current_status}")

        ticket = db.get(Ticket, approval.T_Id)
        order = db.get(Order, ticket.O_Id) if ticket else None
        if order is not None:
            order_status = get_cached_order_status_name_by_id(order.O_StatusId)
            if order_status == OrderStatus.DELIVERED.value and not courier_confirmed:
                log.warning(
                    "approve_action rejected for approval %s: order %s is delivered and courier_confirmed was not set.",
                    approval_id, order.O_Id,
                )
                raise ValueError(
                    "This order is marked as delivered -- confirm the delivery details with the courier "
                    "before approving (check the courier-confirmation box)."
                )

        approval.APST_Id = get_cached_approval_status_id_by_name(ApprovalStatus.APPROVED.value)
        approval.AP_ApproverId = approver_id
        approval.AP_DecidedDate = datetime.now()
        db.add(approval)

        # This is where a real integration would call the payments/wallet
        # service to actually move money. For the MVP, Approval's own
        # AP_ApproverId/AP_DecidedDate are the record that it happened --
        # see design doc Open Questions re: payment-gateway integration
        # (out of scope for v1).

        mark_ticket_resolved(db, approval.T_Id)
        db.commit()
        db.refresh(approval)
        log.info("Approval %s approved by user %s", approval_id, approver_id)
        return approval
    except ValueError:
        db.rollback()
        raise
    except Exception as exc:
        log.error("Unexpected error approving approval %s: %s", approval_id, exc)
        db.rollback()
        raise


def reject_action(db: Session, approval_id: int, approver_id: int, reason: str = None) -> Approval:
    try:
        approval = db.get(Approval, approval_id)
        if approval is None:
            log.warning("reject_action: no such approval %s.", approval_id)
            raise ValueError(f"No such approval: {approval_id}")
        current_status = get_cached_approval_status_name_by_id(approval.APST_Id)
        if current_status != ApprovalStatus.PENDING.value:
            log.warning("reject_action: approval %s is already %s.", approval_id, current_status)
            raise ValueError(f"Approval {approval_id} is already {current_status}")

        approval.APST_Id = get_cached_approval_status_id_by_name(ApprovalStatus.REJECTED.value)
        approval.AP_ApproverId = approver_id
        approval.AP_DecidedDate = datetime.now()
        db.add(approval)

        mark_ticket_resolved(db, approval.T_Id)
        db.commit()
        db.refresh(approval)
        log.info("Approval %s rejected by user %s", approval_id, approver_id)
        return approval
    except ValueError:
        db.rollback()
        raise
    except Exception as exc:
        log.error("Unexpected error rejecting approval %s: %s", approval_id, exc)
        db.rollback()
        raise


def mark_ticket_resolved(db: Session, ticket_id: int) -> None:
    try:
        ticket = db.get(Ticket, ticket_id)
        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.RESOLVED.value)
        ticket.T_ResolvedDate = datetime.now()
        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.SYSTEM.value),
            TM_Message="Your request has been reviewed by our support team and the ticket is now resolved.",
        ))
        db.add(ticket)
    except Exception as exc:
        log.error("Failed to mark ticket %s resolved: %s", ticket_id, exc)
        raise