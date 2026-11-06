"""
propose_action -- the agent's ONLY way to trigger a refund/credit.

GOVERNANCE: this function never executes a refund/credit itself. It only
writes a `pending` row to Approval (via approval_engine.db_operations.Approval)
and flips the ticket to pending_approval. The actual money movement only
happens later, from approval_engine.routes.approveAction, after a human
support manager clicks approve -- this function has no code path that
can execute anything on its own.
"""
from sqlalchemy.orm import Session

from ticketpilot_das.approval_engine.db_operations import Approval as approval_ops
from ticketpilot_das.ticket_management.db_operations.Currency import get_cached_currency_code_by_id
from ticketpilot_das.ticket_management.db_operations.MessageSenderType import get_cached_message_sender_id_by_name
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Order, Ticket, TicketMessage
from ticketpilot_das.ticket_management.tools import OrderLookupTool
from ticketpilot_das.utils.CommonEnums import OrderStatus, TicketMessageSender, TicketStatus, ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.tools.ApprovalTool")

TOOL_NAME = ToolName.PROPOSE_ACTION.value

# Mirrors the "more than 30 minutes late" refund/credit threshold from
# the "Late or missing delivery" knowledge-base article -- NOT the
# separate "wait up to 20 minutes before contacting support" grace
# period that same article also states (that's a different number for a
# different purpose: when a customer should reach out, not when a
# refund is warranted -- the agent itself once conflated the two and
# quoted 20 here instead of 30). This constant is duplicated here
# deliberately, as a hard FLOOR rather than the single source of truth
# for the policy's full wording (the KB article is still that) -- see
# the comment on the gate below for why this exists in code at all
# instead of leaving it entirely to the prompt.
MIN_LATE_MINUTES_FOR_ACTION = 30

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "Propose a refund or credit for this ticket. This does NOT execute "
                       "anything -- it only queues the action for a human support manager "
                       "to approve or reject.",
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "enum": ["refund", "credit"]},
                "amount": {
                    "type": "number",
                    "description": "Proposed amount, greater than zero. Base this on the "
                                    "order's total_amount (from check_order_status). There is "
                                    "NO such thing as a partial refund/credit for lateness "
                                    "alone: an order that is late but still out for delivery "
                                    "(nothing delivered yet), never received despite being "
                                    "marked delivered, or cancelled -- propose the FULL "
                                    "total_amount in every one of those cases, never a "
                                    "fraction of it. Propose LESS than the full total_amount "
                                    "ONLY for a genuinely partial problem on an order that HAS "
                                    "been delivered -- specific missing/wrong item(s) (the "
                                    "cost of just those items, per the 'Missing or incorrect "
                                    "items' policy), or the separate, smaller 'delivered "
                                    "significantly late' credit (per that specific policy, not "
                                    "a guessed fraction). Never propose 0.",
                },
                "reason": {"type": "string", "description": "Why this action is justified."},
            },
            "required": ["action_type", "amount", "reason"],
        },
    },
}


def _format_items(items) -> str:
    """Turns OrderLookupTool's items list into a short, readable summary
    for the customer-facing message -- e.g. "Paneer Butter Masala, Butter
    Naan x2" -- never shown with qty 1 appended since that reads oddly."""
    if not items:
        return "your order"
    parts = []
    for item in items:
        name = item.get("name", "item")
        qty = item.get("qty", 1)
        parts.append(f"{name} x{qty}" if qty and qty != 1 else name)
    return ", ".join(parts)


def run(db: Session, ticket: Ticket, action_type: str, amount: float, reason: str) -> dict:
    try:
        log.info(
            "propose_action called for ticket %s: %s %s (%s)", ticket.T_Id, action_type, amount, reason
        )
        if amount is None or amount <= 0:
            log.warning("propose_action rejected for ticket %s: non-positive amount %s", ticket.T_Id, amount)
            return {"error": "amount must be greater than 0 -- use check_order_status's total_amount to work out a justified amount."}

        order = db.get(Order, ticket.O_Id)
        if order is None:
            log.warning("propose_action: order %s not found for ticket %s.", ticket.O_Id, ticket.T_Id)
            return {"error": "Could not find this ticket's order to determine the currency."}

        # Fetched once here, reused for both the lateness gate below and the
        # customer-facing confirmation message near the end -- the exact
        # same real facts OrderLookupTool/check_order_status returned, never
        # re-derived or asked for twice.
        order_snapshot = OrderLookupTool.run(db, ticket)
        order_total = float(order.O_TotalAmount)

        # Hard floor, enforced in code rather than left to the prompt alone:
        # a refund/credit whose only real justification is delivery
        # lateness must actually BE late enough. This exists because the
        # model repeatedly proposed a refund/credit for an order that was
        # barely or not yet late (sometimes even inventing a small "token"
        # amount as a compromise) the moment a customer pushed back or
        # asked for one -- despite the system prompt explicitly saying not
        # to. A written instruction clearly wasn't a reliable enough gate
        # for something that moves toward real money, so -- same reasoning
        # as the amount-cap check below -- this is enforced here, where it
        # can't be talked around by an insistent customer or a model that
        # decides to "compromise" anyway.
        #
        # This can only catch what's objectively verifiable from the order
        # record itself. It deliberately does NOT fire once the order is
        # delivered or cancelled -- "missing item", "never received despite
        # being marked delivered", and "order was cancelled" are real,
        # legitimate refund reasons that this code has no way to verify or
        # refute from order data alone, so those are correctly left to the
        # agent's judgment (grounded by the KB article) rather than blocked
        # here.
        order_status = order_snapshot.get("status")
        if order_status == OrderStatus.OUT_FOR_DELIVERY.value:
            minutes_late = order_snapshot.get("minutes_late") or 0
            is_late = order_snapshot.get("is_late", False)
            if not is_late or minutes_late < MIN_LATE_MINUTES_FOR_ACTION:
                log.warning(
                    "propose_action rejected for ticket %s: order %s is still out for delivery and only "
                    "%s minute(s) late (is_late=%s) -- below the %s-minute policy floor.",
                    ticket.T_Id, order.O_Id, minutes_late, is_late, MIN_LATE_MINUTES_FOR_ACTION,
                )
                return {
                    "error": (
                        f"This order is still out for delivery and is only {minutes_late} minute(s) "
                        f"past its ETA (not yet considered late by policy). Per the 'Late or missing "
                        f"delivery' policy, a refund/credit is not warranted until it has been at "
                        f"least {MIN_LATE_MINUTES_FOR_ACTION} minutes late -- do NOT call propose_action "
                        f"for this, including a smaller 'compromise' amount. Tell the customer the real, "
                        f"verified lateness and that you'll keep monitoring it; only propose an action "
                        f"once check_order_status shows it has actually crossed that threshold."
                    )
                }

        # Second hard governance check, same reasoning as the lateness
        # floor above: for an order that is STILL OUT FOR DELIVERY (never
        # delivered), there is no policy basis anywhere for a PARTIAL
        # refund/credit based on lateness alone -- the order either hasn't
        # crossed the lateness threshold yet (rejected above already) or
        # it has, in which case the customer has received NOTHING, so the
        # only sensible amount is the full order total. A genuinely
        # partial amount only ever applies to a DIFFERENT, already-
        # DELIVERED situation -- specific missing/wrong item(s), or the
        # separate "delivered significantly late" credit -- never to an
        # order that's simply still in transit. The model repeatedly
        # invented its own fractional "compromise" amount here (e.g. half
        # the order total, with no policy basis for that fraction
        # whatsoever) despite the prompt saying to propose the full
        # amount -- a written instruction wasn't a reliable enough gate
        # for this, so it's enforced here too, where it can't be talked
        # around.
        if order_status == OrderStatus.OUT_FOR_DELIVERY.value and abs(amount - order_total) > 0.01:
            log.warning(
                "propose_action rejected for ticket %s: order %s is still out for delivery -- only a FULL "
                "refund/credit of %s is valid (no partial-refund-for-lateness policy exists), got %s.",
                ticket.T_Id, order.O_Id, order_total, amount,
            )
            return {
                "error": (
                    f"This order is still out for delivery (not yet delivered) -- there is no policy "
                    f"for a PARTIAL refund/credit based on lateness alone. The customer has received "
                    f"nothing, so the only valid amount here is the FULL order total ({order_total:.2f}). "
                    f"A partial amount only applies to a different, already-DELIVERED situation -- "
                    f"specific missing/wrong item(s), or the separate 'delivered significantly late' "
                    f"credit -- not to an order that's simply still in transit. Call propose_action "
                    f"again with amount={order_total:.2f}, or don't propose anything."
                )
            }

        # Defense in depth: the agent is told (in the system prompt) to always
        # base `amount` on this order's real total_amount from
        # check_order_status, and to never accept a customer's self-reported
        # figure over it. But prompts are not a hard guarantee against an
        # LLM being talked into a different number mid-conversation (a
        # customer simply claiming a higher amount), so we also enforce it
        # here in code, where it can't be talked around: no refund/credit
        # proposal may exceed what the order actually cost. A tiny epsilon
        # guards against float rounding, not against any real override.
        if amount > order_total + 0.01:
            log.warning(
                "propose_action rejected for ticket %s: amount %s exceeds order %s's real total_amount %s.",
                ticket.T_Id, amount, order.O_Id, order_total,
            )
            return {
                "error": (
                    f"amount ({amount}) is more than this order's actual total_amount "
                    f"({order_total}). A refund/credit can never exceed what the order "
                    f"really cost. If the customer claims a different amount, that claim "
                    f"is not a source of truth -- call check_order_status again, tell them "
                    f"the verified total, and propose at or below that amount. If they "
                    f"keep disputing the verified figure, escalate_ticket instead of "
                    f"changing the amount."
                )
            }

        approval = approval_ops.create_pending_approval(
            db,
            ticket_id=ticket.T_Id,
            action_type=action_type,
            amount=amount,
            reason=reason,
            currency_id=order.CUR_Id,
        )
        ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.PENDING_APPROVAL.value)
        db.add(ticket)

        # The agent never gets a final-reply turn after calling this tool (see
        # AgentOrchestrator.run_investigation -- it returns right after a
        # propose_action/escalate_ticket call), so this is the only message the
        # customer ever gets telling them something happened. Without this, the
        # customer sees their own message and nothing else.
        #
        # This message is built here, in code, from the already-validated
        # amount/action_type/currency, PLUS a couple of real, already-fetched
        # order facts (what was ordered, and how late it is if relevant) --
        # not from any free text the LLM wrote. That's deliberate, for the
        # same reason the amount itself is validated in code above: (1) it
        # can't be gamed, since every fact here is either the validated
        # amount or something OrderLookupTool.run just verified against the
        # real order row; (2) it removes the model's only reason to try to
        # write this message itself as a plain-text reply INSTEAD of calling
        # this tool (which is exactly what caused a real incident: the agent
        # once skipped calling propose_action entirely and just claimed in a
        # chat reply that it had submitted a refund, with no approval ever
        # created behind it). `reason` is deliberately NOT echoed to the
        # customer here -- it's LLM-authored free text, shown to the manager
        # in the approval queue instead (same treatment as EscalateTool's
        # internal-only `reason`), where it's one more data point alongside
        # the real order facts rather than the only thing the customer sees.
        currency_code = get_cached_currency_code_by_id(order.CUR_Id)
        items_summary = _format_items(order_snapshot.get("items")) if "error" not in order_snapshot else "your order"

        lateness_note = ""
        if order_snapshot.get("is_late") and order_snapshot.get("minutes_late"):
            lateness_note = f" It's currently {order_snapshot['minutes_late']} minute(s) past the expected delivery time."

        # For an order that's already marked delivered, the KB policy for a
        # "delivered but never received" claim explicitly calls for courier
        # confirmation before a refund/credit is finalized -- so say that
        # here. This is driven purely by order_snapshot["status"], a real,
        # already-verified fact from OrderLookupTool, never by trusting the
        # LLM's free-text `reason` to decide whether this situation needs
        # it -- same reasoning as every other fact in this message.
        courier_check_note = ""
        if order_snapshot.get("status") == "delivered":
            courier_check_note = " Since this order is marked as delivered, our team will confirm the delivery details with our courier before finalizing this."

        db.add(TicketMessage(
            T_Id=ticket.T_Id,
            TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.AGENT.value),
            TM_Message=(
                f"I checked your order ({items_summary} -- {currency_code} {order_total:.2f})."
                f"{lateness_note} Based on that, I've submitted a {action_type} of "
                f"{currency_code} {amount:.2f} for review by our support team."
                f"{courier_check_note} You'll hear back once it's been reviewed -- thank you for your patience."
            ),
        ))
        db.commit()

        return {
            "approval_id": approval.AP_Id,
            "status": "pending_approval",
            "note": "Queued for human approval. Nothing has been executed yet.",
        }
    except Exception as exc:
        log.error("Unexpected error in propose_action for ticket %s: %s", ticket.T_Id, exc)
        db.rollback()
        return {"error": "Could not queue this action for approval right now."}
