import { Card, Typography } from "antd";
import { Link } from "react-router-dom";

import config from "../../data/config";
import StatusPill from "../StatusPill/StatusPill";
import { formatDateTime } from "../../utils/helper";

/**
 * Read-only row for the manager dashboard's "Escalated Tickets" panel --
 * there's no in-app "handle this" action for a pure escalation (that
 * happens outside the app, e.g. a phone call), so this is purely a
 * queue of what needs a human's attention, with a link to the full
 * conversation for context.
 */
function EscalatedTicketCard({ ticket }) {
  return (
    <Link to={config.ticketDetailPath(ticket.ticket_id)} target="_blank" rel="noreferrer">
      <Card size="small" hoverable className="qc-ticket-card" style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <Typography.Text strong>Ticket #{ticket.ticket_id} ↗</Typography.Text>
          <StatusPill status="escalated" />
        </div>
        <Typography.Paragraph type="secondary" style={{ marginTop: 4, marginBottom: 0 }} ellipsis={{ rows: 1 }}>
          {ticket.last_message || "No messages yet."}
        </Typography.Paragraph>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Opened {formatDateTime(ticket.created_date)}
        </Typography.Text>
      </Card>
    </Link>
  );
}

export default EscalatedTicketCard;
