import { useEffect, useState } from "react";
import { Alert, Button, Card, Input, Skeleton, Typography } from "antd";
import { SendOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";

import { appendOptimisticMessage, fetchTicket, reopenTicket, sendMessage } from "../../store/ticketSlice";
import TicketMessageThread from "../../components/TicketMessageThread/TicketMessageThread";
import BrandBar from "../../components/BrandBar/BrandBar";
import StatusPill from "../../components/StatusPill/StatusPill";
import Logo from "../../components/Logo/Logo";
import config from "../../data/config";

/**
 * Shows one ticket as a running conversation. Two very different
 * readers land here, and both now always have a session (customers log
 * in too, as of this pivot) -- so the role claim, not session presence,
 * is what decides which view renders:
 *  - A logged-in customer -- the full branded chat, composer included.
 *  - A logged-in support manager, arriving from an ApprovalCard /
 *    EscalatedTicketCard / the All Tickets list -- a plain, read-only
 *    view of the same conversation for context. No composer: a manager
 *    reviewing a ticket should never be able to type into it pretending
 *    to be the customer.
 */
function TicketDetail() {
  const { ticketId } = useParams();
  const dispatch = useDispatch();
  const { currentTicket, status, error } = useSelector((state) => state.tickets);
  const session = useSelector((state) => state.session.user);
  const isManagerView = session?.role === "support_manager";
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState(null);

  useEffect(() => {
    dispatch(fetchTicket(ticketId));
  }, [dispatch, ticketId]);

  const sending = status === "loading" && !!currentTicket;

  const handleSend = async () => {
    if (!draft.trim() || sending) return;
    setSendError(null);
    const isResolved = currentTicket.status === "resolved";
    const messageToSend = draft;

    // Show the customer's own message right away instead of waiting for
    // the agent's full reply to come back -- the composer clears
    // immediately too, same as any real chat app.
    setDraft("");
    dispatch(appendOptimisticMessage({ message: messageToSend }));

    try {
      if (isResolved) {
        await dispatch(reopenTicket({ ticketId, message: messageToSend })).unwrap();
      } else {
        await dispatch(sendMessage({ ticketId, message: messageToSend })).unwrap();
      }
    } catch (err) {
      setSendError(err?.response?.data?.detail || "Could not send your message. Please try again.");
      setDraft(messageToSend); // give them their draft back so nothing is lost
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (status === "loading" && !currentTicket) {
    return (
      <div className="page-shell">
        <Skeleton active />
      </div>
    );
  }

  if (!currentTicket) {
    return (
      <div className="page-shell">
        {error && <Alert type="error" message={error} />}
      </div>
    );
  }

  const isResolved = currentTicket.status === "resolved";
  const isHumanOwned = currentTicket.status === "escalated" || currentTicket.status === "pending_approval";

  return (
    <>
      {!isManagerView && <BrandBar />}
      <div className="page-shell" style={{ maxWidth: 640 }}>
      <Typography.Paragraph style={{ marginBottom: 12 }}>
        <Link to={isManagerView ? config.routes.approvalQueue : config.routes.submitTicket}>
          <ArrowLeftOutlined /> Back
        </Link>
      </Typography.Paragraph>

      <div className="chat-header">
        {!isManagerView && (
          <div className="chat-header__avatar">
            <Logo size={26} />
          </div>
        )}
        <div className="chat-header__info">
          <div className="chat-header__name">
            {isManagerView ? `Ticket #${currentTicket.ticket_id}` : "TicketPilot Agent"}
          </div>
          <div className="chat-header__status">
            {isManagerView
              ? `Customer #${currentTicket.customer_id} · Order #${currentTicket.order_id}`
              : `Order #${currentTicket.order_id} · Ticket #${currentTicket.ticket_id}`}
          </div>
        </div>
        <StatusPill status={currentTicket.status} />
      </div>

      {isManagerView && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="Read-only view for context."
          description="You're viewing this conversation as a support manager -- replying here isn't available. Approve/reject proposed actions from the dashboard."
        />
      )}

      {!isManagerView && isHumanOwned && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={
            currentTicket.status === "escalated"
              ? "A support manager is now handling this ticket directly."
              : "A support manager is reviewing a proposed refund/credit for this ticket."
          }
          description="You can still send a message below -- it'll be visible to whoever's handling this, though our AI agent won't reply again until it's resolved."
        />
      )}

      <Card className="chat-card" bodyStyle={{ padding: "12px 16px" }}>
        <TicketMessageThread messages={currentTicket.messages} typing={!isManagerView && sending} />
      </Card>

      {!isManagerView && (
        <>
          {sendError && (
            <Alert type="error" message={sendError} style={{ margin: "12px 0" }} closable onClose={() => setSendError(null)} />
          )}

          <div className="chat-composer">
            {isResolved && (
              <Typography.Text type="secondary" style={{ display: "block", marginBottom: 6, fontSize: 13 }}>
                This ticket is resolved. Sending a message will reopen it so the agent can pick it back up.
              </Typography.Text>
            )}
            <div className="chat-composer__row">
              <Input.TextArea
                autoSize={{ minRows: 1, maxRows: 4 }}
                placeholder={isResolved ? "Still not resolved? Tell us what's wrong..." : "Type a message..."}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
              />
              <Button
                type="primary"
                shape="circle"
                icon={<SendOutlined />}
                onClick={handleSend}
                loading={sending}
                disabled={!draft.trim()}
              />
            </div>
          </div>
        </>
      )}
      </div>
    </>
  );
}

export default TicketDetail;
