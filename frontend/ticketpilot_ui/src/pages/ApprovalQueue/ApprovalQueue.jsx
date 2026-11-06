import { useEffect } from "react";
import { Badge, Empty, Skeleton, Typography } from "antd";
import { useDispatch, useSelector } from "react-redux";

import { fetchPendingApprovals } from "../../store/approvalSlice";
import { fetchAllTickets, fetchEscalatedTickets } from "../../store/ticketSlice";
import ApprovalCard from "../../components/ApprovalCard/ApprovalCard";
import EscalatedTicketCard from "../../components/EscalatedTicketCard/EscalatedTicketCard";
import AllTicketsTable from "../../components/AllTicketsTable/AllTicketsTable";

/**
 * Support manager's dashboard -- a plain, sober internal tool (no
 * cartoonish colors, no card-grid-with-emojis, that's the customer
 * side). Three sections:
 *  1. Pending Approvals: every proposed refund/credit (ApprovalTool),
 *     actionable here (approve/reject).
 *  2. Escalated Tickets: everything the agent handed off outright
 *     (EscalateTool) -- read-only, just a queue of what needs a human,
 *     with a link into the full conversation for context.
 *  3. All Tickets: every ticket raised, across every customer -- a
 *     real list, not a customer_id search box.
 */
function ApprovalQueue() {
  const dispatch = useDispatch();
  const { pending, status } = useSelector((state) => state.approvals);
  const { escalated, escalatedStatus, all, allStatus } = useSelector((state) => state.tickets);

  useEffect(() => {
    dispatch(fetchPendingApprovals());
    dispatch(fetchEscalatedTickets());
    dispatch(fetchAllTickets());
  }, [dispatch]);

  return (
    <div className="qc-manager-shell">
      <Typography.Title level={4} className="qc-section-title">
        <Badge count={pending.length} showZero className="qc-manager-badge" /> Pending Approvals
      </Typography.Title>

      {status === "loading" && pending.length === 0 && <Skeleton active />}
      {status !== "loading" && pending.length === 0 && <Empty description="Nothing waiting on you right now." />}

      {pending.map((approval) => (
        <ApprovalCard key={approval.approval_id} approval={approval} />
      ))}

      <Typography.Title level={4} className="qc-section-title" style={{ marginTop: 32 }}>
        <Badge count={escalated.length} showZero className="qc-manager-badge" /> Escalated Tickets
      </Typography.Title>

      {escalatedStatus === "loading" && escalated.length === 0 && <Skeleton active />}
      {escalatedStatus !== "loading" && escalated.length === 0 && (
        <Empty description="No tickets currently escalated." />
      )}

      {escalated.map((ticket) => (
        <EscalatedTicketCard key={ticket.ticket_id} ticket={ticket} />
      ))}

      <Typography.Title level={4} className="qc-section-title" style={{ marginTop: 32 }}>
        <Badge count={all.length} showZero className="qc-manager-badge" /> All Tickets
      </Typography.Title>

      <AllTicketsTable tickets={all} loading={allStatus === "loading" && all.length === 0} />
    </div>
  );
}

export default ApprovalQueue;
