import { useEffect, useState } from "react";
import { Alert, Button, Card, Checkbox, Input, Skeleton, Space, Tag, Typography } from "antd";
import { useDispatch } from "react-redux";

import { approveAction, rejectAction } from "../../store/approvalSlice";
import { getTicketService } from "../../utils/apiHelper";
import TicketMessageThread from "../TicketMessageThread/TicketMessageThread";
import styles from "./ApprovalCard.module.css";

const titleCase = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

/**
 * One pending Approval, redesigned so a manager can decide WITHOUT
 * opening a separate tab: the customer's issue, the real order details,
 * which knowledge-base policy (if any) the agent matched, the agent's
 * own reasoning, and the full chat -- all inline, then Approve/Reject.
 * Approving is the ONLY action in the entire app that actually moves
 * money -- see approval_engine.db_operations.Approval.approve_action.
 *
 * Order details / policy / chat come from GET /getTicket, fetched here
 * directly (not through the shared ticketSlice.currentTicket, which is
 * a single-ticket slot that several of these cards rendering at once
 * would clobber for each other).
 */
function ApprovalCard({ approval }) {
  const dispatch = useDispatch();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [ticket, setTicket] = useState(null);
  const [ticketError, setTicketError] = useState(null);
  const [showChat, setShowChat] = useState(false);
  const [courierConfirmed, setCourierConfirmed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getTicketService(approval.ticket_id)
      .then((data) => {
        if (!cancelled) setTicket(data);
      })
      .catch(() => {
        if (!cancelled) setTicketError("Could not load this ticket's details.");
      });
    return () => {
      cancelled = true;
    };
  }, [approval.ticket_id]);

  const handleApprove = async () => {
    setSubmitting(true);
    try {
      await dispatch(approveAction({ approvalId: approval.approval_id, courierConfirmed })).unwrap();
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    setSubmitting(true);
    try {
      await dispatch(rejectAction({ approvalId: approval.approval_id, reason })).unwrap();
    } finally {
      setSubmitting(false);
    }
  };

  const customerIssue = ticket?.messages?.find((m) => m.sender === "customer")?.message;
  const order = ticket?.order;
  // The same condition the backend enforces server-side (see
  // approval_engine.db_operations.Approval.approve_action) -- a delivered
  // order needs courier confirmation before a refund/credit can be
  // approved. Kept in sync with that check so the UI never promises an
  // approve the backend will actually refuse.
  const needsCourierConfirmation = order?.status === "delivered";
  const policyHits = (ticket?.investigation_trail || [])
    .filter((step) => step.tool === "search_knowledge_base")
    .flatMap((step) => step.result?.results || []);

  return (
    <Card size="small" className={styles.card}>
      <Space direction="vertical" style={{ width: "100%" }} size={12}>
        <div className={styles.header}>
          <Typography.Text strong>Ticket #{approval.ticket_id}</Typography.Text>
          <Tag>{`${approval.action_type.toUpperCase()} — ₹${approval.amount.toFixed(2)}`}</Tag>
        </div>

        {ticketError && <Alert type="warning" showIcon message={ticketError} />}

        {!ticket && !ticketError && <Skeleton active paragraph={{ rows: 2 }} />}

        {ticket && (
          <>
            <div className={styles.section}>
              <span className={styles.sectionLabel}>Customer's issue</span>
              <div className={styles.issueText}>{customerIssue || "—"}</div>
            </div>

            {order && (
              <div className={styles.section}>
                <span className={styles.sectionLabel}>Order details</span>
                <div className={styles.orderGrid}>
                  <span>
                    Items: <b>{(order.items || []).map((i) => `${i.name}${i.qty > 1 ? ` x${i.qty}` : ""}`).join(", ") || "—"}</b>
                  </span>
                  <span>
                    Total: <b>{order.currency} {Number(order.total_amount).toFixed(2)}</b>
                  </span>
                  <span>
                    Status: <b>{titleCase(order.status)}</b>
                  </span>
                  {order.is_late && (
                    <span>
                      Late by: <b>{order.minutes_late} min</b>
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className={styles.section}>
              <span className={styles.sectionLabel}>Policy the agent matched</span>
              {policyHits.length > 0 ? (
                <Space size={6} wrap>
                  {policyHits.map((hit, idx) => (
                    <span className={styles.policyChip} key={idx}>{hit.title}</span>
                  ))}
                </Space>
              ) : (
                <span className={styles.noPolicy}>No knowledge-base article was consulted for this one.</span>
              )}
            </div>

            <div className={styles.section}>
              <span className={styles.sectionLabel}>Agent's reasoning</span>
              <Typography.Paragraph style={{ marginBottom: 0 }}>{approval.reason}</Typography.Paragraph>
            </div>

            <div className={styles.section}>
              <Button type="link" className={styles.chatToggle} onClick={() => setShowChat((v) => !v)}>
                {showChat ? "Hide full conversation ▲" : "Show full conversation ▼"}
              </Button>
              {showChat && (
                <div className={styles.chatBox} style={{ marginTop: 8 }}>
                  <TicketMessageThread messages={ticket.messages} />
                </div>
              )}
            </div>
          </>
        )}

        {needsCourierConfirmation && (
          <Alert
            type="warning"
            showIcon
            message="This order is marked as delivered"
            description={
              <Checkbox
                checked={courierConfirmed}
                onChange={(e) => setCourierConfirmed(e.target.checked)}
              >
                I've confirmed the delivery details with our courier
              </Checkbox>
            }
          />
        )}

        {rejecting && (
          <Input.TextArea
            rows={2}
            placeholder="Optional reason for rejecting"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}

        <Space>
          <Button
            type="primary"
            onClick={handleApprove}
            loading={submitting}
            disabled={needsCourierConfirmation && !courierConfirmed}
          >
            Approve
          </Button>
          {rejecting ? (
            <Button danger onClick={handleReject} loading={submitting}>
              Confirm reject
            </Button>
          ) : (
            <Button onClick={() => setRejecting(true)}>Reject</Button>
          )}
        </Space>
      </Space>
    </Card>
  );
}

export default ApprovalCard;
