"""FastAPI routes for approval_engine. All three require a logged-in
support manager (JWT) -- these are the endpoints that move money."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ticketpilot_das.approval_engine.db_operations import Approval as approval_ops
from ticketpilot_das.approval_engine.db_operations.ApprovalActionType import get_cached_approval_action_name_by_id
from ticketpilot_das.approval_engine.db_operations.ApprovalStatusType import get_cached_approval_status_name_by_id
from ticketpilot_das.approval_engine.entity.PydanticModels import ApprovalOut, ApproveActionRequest, RejectActionRequest
from ticketpilot_das.auth.db_operations.Auth import get_current_user
from ticketpilot_das.auth.entity.DbModels import User
from ticketpilot_das.ticket_management.db_operations.Currency import get_cached_currency_code_by_id
from ticketpilot_das.utils.Database import get_db
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("approval_engine.routes.Approval")

router = APIRouter(prefix="/approvalengine", tags=["approval_engine"])


@router.get("/getPendingApprovals", response_model=list[ApprovalOut])
def get_pending_approvals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Function: getPendingApprovals
    Description: Lists every approval still awaiting a human decision --
        feeds the support manager's approval queue in the frontend.
    Inputs: none (auth via JWT).
    Outputs: list of pending approvals, oldest first.
    Happy Flow: returns the queue.
    Error Flow: missing/invalid JWT -> 401.
    """
    try:
        approvals = approval_ops.get_pending_approvals(db)
        return [to_out(a) for a in approvals]
    except Exception as exc:
        log.error("Failed to list pending approvals: %s", exc)
        raise HTTPException(status_code=500, detail="Could not load pending approvals.")


@router.post("/approveAction/{approval_id}", response_model=ApprovalOut)
def approve_action(
    approval_id: int,
    payload: ApproveActionRequest = ApproveActionRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Function: approveAction
    Description: The ONLY endpoint that actually causes a refund/credit
        to be executed -- records the approving user and decided date,
        and resolves the ticket.
    Inputs: approval_id (path), courier_confirmed (body, defaults False --
        only actually required when the order is already delivered; see
        approval_ops.approve_action), current_user from JWT.
    Outputs: the updated approval.
    Happy Flow: approval is pending (and courier_confirmed if required)
        -> approved, ticket resolved.
    Error Flow: approval doesn't exist, or isn't pending -> 400/404. Order
        is delivered and courier_confirmed wasn't sent -> 400.
    """
    try:
        log.info(
            "POST approveAction -- approval_id=%s by user=%s courier_confirmed=%s",
            approval_id, current_user.U_Id, payload.courier_confirmed,
        )
        approval = approval_ops.approve_action(db, approval_id, current_user.U_Id, payload.courier_confirmed)
        return to_out(approval)
    except ValueError as exc:
        log.warning("approveAction rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in approveAction %s: %s", approval_id, exc)
        raise HTTPException(status_code=500, detail="Could not approve this action.")


@router.post("/rejectAction/{approval_id}", response_model=ApprovalOut)
def reject_action(
    approval_id: int,
    payload: RejectActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Function: rejectAction
    Description: Records that a human declined the agent's proposed
        action -- nothing is executed, ticket is resolved with the
        rejection noted.
    Inputs: approval_id (path), optional reason, current_user from JWT.
    Outputs: the updated approval.
    Happy Flow: approval is pending -> rejected, ticket resolved.
    Error Flow: approval doesn't exist, or isn't pending -> 400/404.
    """
    try:
        log.info("POST rejectAction -- approval_id=%s by user=%s", approval_id, current_user.U_Id)
        approval = approval_ops.reject_action(db, approval_id, current_user.U_Id, payload.reason)
        return to_out(approval)
    except ValueError as exc:
        log.warning("rejectAction rejected: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("Unexpected error in rejectAction %s: %s", approval_id, exc)
        raise HTTPException(status_code=500, detail="Could not reject this action.")


def to_out(approval) -> ApprovalOut:
    return ApprovalOut(
        approval_id=approval.AP_Id,
        ticket_id=approval.T_Id,
        action_type=get_cached_approval_action_name_by_id(approval.APAT_Id),
        amount=float(approval.AP_Amount),
        currency=get_cached_currency_code_by_id(approval.CUR_Id),
        reason=approval.AP_Reason,
        status=get_cached_approval_status_name_by_id(approval.APST_Id),
        approver_id=approval.AP_ApproverId,
        decided_date=approval.AP_DecidedDate,
    )
