"""
AgentOrchestrator -- the tool-calling loop at the heart of TicketPilot.

WHAT THIS IS, IN PLAIN TERMS
-----------------------------
This is the piece that plays the same role Claude itself plays when it reads
a task, decides which of ITS registered tools to call (Read, Bash, etc.),
gets real results back, and keeps going until it has a final answer. Here,
the "task" is one support ticket, and the registered tools are the 5
functions below -- nothing else is callable, by design (see "Tool
Governance").

HOW THE LOOP ACTUALLY WORKS
----------------------------
1. Load the ticket's full TicketMessage history (not just the latest
   message) and turn it into a normal chat-style message list. This is
   what gives the agent "memory" of a multi-turn conversation and of a
   reopened ticket -- there is no separate, more complex memory system,
   just the same transcript replayed every time.
2. Send that message list, plus the JSON schema for each of the 5
   registered tools, to the LLM.
3. The LLM can respond in one of two ways:
     a) a tool_call -- "run check_order_status" (no arguments needed
        beyond the ticket context), or "run propose_action with these
        arguments". We execute ONLY the matching Python function below,
        feed its real result back to the LLM as a new message, and loop.
     b) plain text -- the LLM is done investigating and is giving its
        final reply directly to the customer. We save that as the
        resolution and stop.
4. propose_action and escalate_ticket are themselves tools (not a separate
   "decision" step) -- calling one of them IS the decision, and it already
   updates the ticket's status as a side effect (see each tool's `run()`).
5. The whole call stays synchronous: submitTicket's HTTP request does not
   return to the customer until this loop finishes one way or another.
6. A hard cap on iterations (Configuration.MAX_TOOL_CALLS) stops a runaway
   loop from calling tools forever; if it's hit, we escalate automatically
   rather than silently doing nothing.

CONVERSATION CONTEXT
---------------------
Every message -- the customer's original complaint, each tool result, the
agent's final reply, a later reopen message -- is appended to TicketMessage
as it happens (tool-call traffic is kept in Ticket.T_InvestigationTrail
instead, since customers shouldn't see raw tool JSON). The next time this
ticket is touched (a reopen, or a follow-up), we reload the same
TicketMessage history, so the agent already has the full context without
us building any bespoke "memory" layer.

TOOL GOVERNANCE
-----------------
Two layers, matching the design doc:
  1. Closed-set tool-calling API -- the LLM is only ever told about the 5
     schemas in TOOL_SCHEMAS below, and TOOL_SCHEMAS is the only dict this
     file will ever dispatch a tool_call name against. A tool name it
     invents that isn't registered is rejected, not executed.
  2. Each tool enforces its OWN scope in code (see each tool module's
     docstring) -- e.g. check_order_status always re-derives the order
     from the ticket's own customer, never from an argument the model
     supplies. So even a compromised or confused model can't widen what
     it's allowed to touch just by asking.
"""
import json
import re
from typing import List

from openai import OpenAI, RateLimitError
from retrying import retry
from sqlalchemy.orm import Session

from ticketpilot_das.ticket_management.db_operations.MessageSenderType import (
    get_cached_message_sender_id_by_name,
)
from ticketpilot_das.ticket_management.db_operations.TicketStatusType import get_cached_ticket_status_id_by_name
from ticketpilot_das.ticket_management.entity.DbModels import Ticket, TicketMessage
from ticketpilot_das.ticket_management.tools import (
    AccountLookupTool,
    ApprovalTool,
    CloseTicketTool,
    EscalateTool,
    KnowledgeSearchTool,
    OrderLookupTool,
)
from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.CommonEnums import LlmRole, TicketMessageSender, TicketStatus, ToolName
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("ticket_management.AgentOrchestrator")

# The actual wording lives in data/prompts/system_prompt.txt (read once into
# Configuration.SYSTEM_PROMPT at startup) -- not hardcoded here, so a
# non-engineer can tweak the agent's tone/instructions without touching code.

# The closed set. The LLM is only ever told about these 6 schemas, and this
# list is the only thing a tool_call name is ever looked up against.
TOOL_SCHEMAS = [
    OrderLookupTool.TOOL_SCHEMA,
    AccountLookupTool.TOOL_SCHEMA,
    KnowledgeSearchTool.TOOL_SCHEMA,
    ApprovalTool.TOOL_SCHEMA,
    EscalateTool.TOOL_SCHEMA,
    CloseTicketTool.TOOL_SCHEMA,
]


#  A real incident: the agent, asked to explain its decisions with real
# specifics, found that propose_action's own confirmation message is fixed
# (built in code, not by the LLM -- see ApprovalTool.run()), so instead of
# calling the tool it just wrote a convincing plain-text reply CLAIMING a
# refund had been submitted. No approval row was ever created; no human
# ever saw it; the ticket closed as if everything had gone through.
#
# The prompt has since been tightened (see "## Explaining decisions" in
# system_prompt.txt) and ApprovalTool's own message was made specific
# enough that the model has no real reason to compete with it. This is the
# second, code-level backstop -- the same defense-in-depth pattern as
# ApprovalTool's own amount cap. By the time run_investigation reaches a
# plain-text reply, we already know for certain that no propose_action /
# escalate_ticket call succeeded THIS run (a successful one returns
# immediately, before the LLM is ever called again -- see the loop below).
# So if the reply text STILL claims one of those things happened, that is
# never legitimate -- it's either a leftover hallucination of this same
# pattern, or some other hallucinated completion claim -- and it must never
# reach the customer as-is.
_FALSE_ACTION_CLAIM_PHRASES = (
    "i've submitted", "i have submitted",
    "submitted a refund", "submitted a credit",
    "queued a refund", "queued a credit",
    "issued a refund", "issued a credit",
    "processed a refund", "processed a credit",
    "escalated this ticket", "escalated to a human",
    "passed this along", "forwarded this to",
    # Added after a real incident: the tool is literally named
    # propose_action, and the model naturally describes using it with
    # "propose"/"proposed" language -- which the phrase list above
    # entirely missed. The model said "I will propose a full refund of
    # X..." (future tense, no tool call this turn) and then, next turn,
    # "I've already proposed a full refund..." -- neither matched any
    # phrase above, so both reached the customer as fact with no
    # Approval row ever created behind them.
    "i will propose", "i'll propose",
    "i've proposed", "i have proposed", "already proposed",
    "propose a refund", "propose a credit",
    "proposed a refund", "proposed a credit",
)

# Second, broader backstop -- a plain-text reply only ever reaches this
# function when we already know (see the module-level note above) that no
# propose_action/escalate_ticket call succeeded THIS run. The only place a
# customer should see a specific PROPOSED/COMPLETED amount is
# propose_action's own fixed confirmation message, which bypasses this
# function entirely (the loop returns before the LLM is called again). So a
# currency amount directly TIED to refund/credit language in free text here
# -- "refund of INR 420", "INR 420 credit", etc. -- is, by construction, the
# model narrating a decision that cannot have actually happened, regardless
# of which verb it used. This exists specifically because the literal
# phrase list above is inherently incomplete (the model can always phrase
# the same false claim a new way); this check doesn't depend on guessing
# the exact wording.
#
# IMPORTANT -- this must only match the amount actually sitting next to
# refund/credit language, NOT merely co-occurring anywhere in the same
# reply. A real incident: the agent legitimately explains the order's real
# total while explaining refund ELIGIBILITY -- e.g. "...a total amount of
# INR 420.00... a refund or credit is not warranted until the order is at
# least 30 minutes late" -- which is a completely truthful, grounded answer
# (the order total came from check_order_status), not a false completed-
# action claim. An earlier, looser version of this pattern treated ANY
# currency amount anywhere near the words "refund"/"credit" in the whole
# reply as a false claim, which silently escalated and hid perfectly
# correct replies like that one from the customer on multiple tickets --
# every single time the agent mentioned the order total while discussing
# the refund policy. Scoping the match to the amount sitting immediately
# next to refund/credit wording (not just present somewhere in the same
# paragraph) fixes that false-positive while still catching the real
# failure mode ("I've issued a refund of INR 420", "INR 420 credit is on
# its way", etc.).
_CURRENCY_REFUND_CLAIM_PATTERN = re.compile(
    r"(?:refund|credit)\s*(?:of|for|:)?\s*(?:₹|inr)\s*[\d,]+(?:\.\d{1,2})?"
    r"|(?:₹|inr)\s*[\d,]+(?:\.\d{1,2})?\s*(?:refund|credit)",
    re.IGNORECASE,
)


def _claims_unperformed_action(reply_text: str) -> bool:
    """See the module-level note above this function for why this check is
    safe to rely on (not just a guess): reaching here already guarantees no
    decision tool succeeded this run."""
    lowered = reply_text.lower()
    if any(phrase in lowered for phrase in _FALSE_ACTION_CLAIM_PHRASES):
        return True
    if _CURRENCY_REFUND_CLAIM_PATTERN.search(reply_text):
        return True
    return False


def build_message_history(ticket: Ticket, db: Session) -> List[dict]:
    messages = [{"role": LlmRole.SYSTEM.value, "content": Configuration.SYSTEM_PROMPT}]
    customer_sender_id = get_cached_message_sender_id_by_name(TicketMessageSender.CUSTOMER.value)
    for msg in ticket.messages:
        # Translate OUR sender vocabulary (TM_SenderId -> customer/agent/system)
        # into the LLM API's OWN, separate vocabulary (role: user/assistant) --
        # "assistant" means "something the AI itself said in a previous turn".
        role = LlmRole.USER.value if msg.TM_SenderId == customer_sender_id else LlmRole.ASSISTANT.value
        messages.append({"role": role, "content": msg.TM_Message})
    return messages


def _is_retryable_llm_error(exc: BaseException) -> bool:
    """Only a genuine transient/rate-limit failure should be retried -- a
    real bug (bad request, auth failure, model not found, etc.) should fail
    immediately instead of silently retrying 3 times for nothing. Same idea
    as the reference codebase's retry_if_mysql_error, just scoped to the
    LLM call instead of a DB call."""
    return isinstance(exc, RateLimitError)


@retry(
    stop_max_attempt_number=Configuration.LLM_RETRY_ATTEMPTS,
    wait_exponential_multiplier=Configuration.LLM_RETRY_WAIT_MULTIPLIER_MS,
    wait_exponential_max=Configuration.LLM_RETRY_MAX_WAIT_MS,
    retry_on_exception=_is_retryable_llm_error,
)
def call_llm(messages: List[dict], tools: List[dict]):
    """Calls the LLM via OpenRouter (OpenAI-compatible API) rather than
    OpenAI directly -- OpenRouter is a multi-provider router that exposes
    the same /chat/completions shape, so only base_url + model + key change.
    Nothing else in this file needs to change, since everything else only
    deals in plain message dicts and tool_call dicts.

    Wrapped with @retry so a transient 429 (upstream provider's shared pool
    momentarily out of capacity -- see RateLimitError) gets retried with
    exponential backoff instead of failing the whole ticket submission on
    the first hiccup. Any other error (bad request, auth, etc.) is NOT
    retried -- it fails immediately via _is_retryable_llm_error above."""
    try:
        client = OpenAI(base_url=Configuration.LLM_BASE_URL, api_key=Configuration.LLM_API_KEY)
        log.debug("Calling LLM model=%s via %s", Configuration.LLM_MODEL, Configuration.LLM_BASE_URL)
        response = client.chat.completions.create(
            model=Configuration.LLM_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        return response.choices[0].message
    except RateLimitError as exc:
        log.warning("LLM call rate-limited, will retry if attempts remain: %s", exc)
        raise
    except Exception as exc:
        log.error("LLM call failed: %s", exc)
        raise


def execute_tool(db: Session, ticket: Ticket, tool_name: str, arguments: dict) -> dict:
    """The ONLY dispatch point for tool_calls. Anything not registered is
    refused outright -- it is never executed, no matter what the model asks for."""
    if tool_name == ToolName.CHECK_ORDER_STATUS.value:
        return OrderLookupTool.run(db, ticket)
    if tool_name == ToolName.CHECK_ACCOUNT_HISTORY.value:
        return AccountLookupTool.run(db, ticket)
    if tool_name == ToolName.SEARCH_KNOWLEDGE_BASE.value:
        return KnowledgeSearchTool.run(query=arguments.get("query", ""))
    if tool_name == ToolName.PROPOSE_ACTION.value:
        return ApprovalTool.run(
            db, ticket,
            action_type=arguments["action_type"],
            amount=arguments["amount"],
            reason=arguments["reason"],
        )
    if tool_name == ToolName.ESCALATE_TICKET.value:
        return EscalateTool.run(db, ticket, reason=arguments["reason"])
    if tool_name == ToolName.CLOSE_TICKET.value:
        return CloseTicketTool.run(db, ticket, closing_message=arguments["closing_message"])

    log.warning("Model tried to call an unregistered tool: %s -- refused.", tool_name)
    return {"error": f"Tool '{tool_name}' is not registered. This call was refused."}


def run_investigation(db: Session, ticket_id: int) -> None:
    """Runs the full tool-calling loop for one ticket, synchronously, and
    persists the outcome. Called by submit_ticket() and reopen_ticket()."""
    try:
        ticket = db.get(Ticket, ticket_id)
        messages = build_message_history(ticket, db)
        trail = []

        for call_count in range(Configuration.MAX_TOOL_CALLS):
            assistant_message = call_llm(messages, TOOL_SCHEMAS)

            if not assistant_message.tool_calls:
                # Plain text -- the agent has answered (or is asking a
                # clarifying question), but this does NOT close the ticket
                # anymore. Real support tickets stay open until the customer
                # confirms they're satisfied; the agent's own system prompt
                # tells it to ask "anything else?" here. The ticket only
                # becomes RESOLVED when the agent later calls close_ticket
                # (below), once the customer has actually confirmed that.
                reply_text = assistant_message.content or ""

                if _claims_unperformed_action(reply_text):
                    # Don't show this to the customer at all -- it describes
                    # something that never actually happened. Escalate
                    # instead, with the suspect reply preserved for whoever
                    # picks this up, and stop here (same return shape as any
                    # other decision-tool outcome below).
                    log.warning(
                        "Ticket %s: agent's plain-text reply claims a refund/credit/escalation "
                        "was submitted, but no such tool call succeeded this run -- withholding "
                        "it from the customer and escalating instead. Original reply: %r",
                        ticket.T_Id, reply_text,
                    )
                    EscalateTool.run(
                        db, ticket,
                        reason=(
                            "Agent's reply claimed to have submitted a refund/credit or escalated "
                            "this ticket without actually calling the corresponding tool -- needs "
                            "human review. Unsent reply was: " + reply_text
                        ),
                    )
                    ticket.T_InvestigationTrail = trail
                    db.add(ticket)
                    db.commit()
                    return

                db.add(TicketMessage(
                    T_Id=ticket.T_Id,
                    TM_SenderId=get_cached_message_sender_id_by_name(TicketMessageSender.AGENT.value),
                    TM_Message=reply_text,
                ))
                investigating_id = get_cached_ticket_status_id_by_name(TicketStatus.INVESTIGATING.value)
                if ticket.T_StatusId == investigating_id:
                    ticket.T_StatusId = get_cached_ticket_status_id_by_name(TicketStatus.AWAITING_CUSTOMER.value)
                ticket.T_InvestigationTrail = trail
                db.add(ticket)
                db.commit()
                log.info("Ticket %s replied to by the agent -- awaiting the customer.", ticket.T_Id)
                return

            messages.append({"role": LlmRole.ASSISTANT.value, "tool_calls": assistant_message.tool_calls})

            for tool_call in assistant_message.tool_calls:
                arguments = json.loads(tool_call.function.arguments or "{}")
                result = execute_tool(db, ticket, tool_call.function.name, arguments)
                trail.append({"tool": tool_call.function.name, "arguments": arguments, "result": result})
                messages.append({
                    "role": LlmRole.TOOL.value,
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })

                # propose_action / escalate_ticket / close_ticket already
                # changed ticket status as a side effect inside their own
                # run() -- but ONLY when they actually succeeded. Each of
                # these tools validates its own inputs internally (e.g.
                # ApprovalTool rejects a non-positive amount) and returns an
                # {"error": ...} dict WITHOUT touching the ticket's status
                # when rejected -- it does not raise. If we stopped the loop
                # here regardless of outcome, a rejected call (e.g. the LLM
                # calling propose_action with a placeholder amount of 0
                # before it has actually looked up the order) would leave
                # the ticket permanently stuck at "investigating" with no
                # reply and no error ever surfaced to the caller. So we only
                # treat this as a final decision when the result has no
                # "error" key -- on a rejection, the error is already in the
                # tool-result message appended above, and the loop simply
                # continues so the LLM can see why it failed and retry
                # properly (e.g. call check_order_status first).
                if (
                    tool_call.function.name in (
                        ToolName.PROPOSE_ACTION.value,
                        ToolName.ESCALATE_TICKET.value,
                        ToolName.CLOSE_TICKET.value,
                    )
                    and "error" not in result
                ):
                    ticket.T_InvestigationTrail = trail
                    db.add(ticket)
                    db.commit()
                    log.info(
                        "Ticket %s decision made via tool '%s'.", ticket.T_Id, tool_call.function.name
                    )
                    return
                elif "error" in result:
                    log.info(
                        "Ticket %s: tool '%s' was rejected (%s) -- continuing the loop so the "
                        "agent can retry instead of leaving the ticket stuck.",
                        ticket.T_Id, tool_call.function.name, result.get("error"),
                    )

        # Safety net: ran out of tool-call budget without a final decision.
        log.warning("Ticket %s hit MAX_TOOL_CALLS without a decision -- auto-escalating.", ticket.T_Id)
        EscalateTool.run(db, ticket, reason="Investigation loop did not reach a decision in time.")
        ticket.T_InvestigationTrail = trail
        db.add(ticket)
        db.commit()
    except Exception as exc:
        log.error("Unexpected error running investigation for ticket %s: %s", ticket_id, exc)
        db.rollback()
        raise
