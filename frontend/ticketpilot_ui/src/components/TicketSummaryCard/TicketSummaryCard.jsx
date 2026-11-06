import { Card, Typography } from "antd";
import { Link } from "react-router-dom";

import config from "../../data/config";
import StatusPill from "../StatusPill/StatusPill";
import { formatDateTime } from "../../utils/helper";

function TicketSummaryCard({ ticket }) {
  return (
    <Link to={config.ticketDetailPath(ticket.ticket_id)}>
      <Card size="small" hoverable className="qc-ticket-card" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <Typography.Text strong>Ticket #{ticket.ticket_id}</Typography.Text>
          <StatusPill status={ticket.status} />
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

export default TicketSummaryCard;
