import { Table, Typography } from "antd";
import { useNavigate } from "react-router-dom";

import config from "../../data/config";
import StatusPill from "../StatusPill/StatusPill";
import { formatDateTime } from "../../utils/helper";

/**
 * Plain list of every ticket raised, across every customer -- this is
 * what the manager asked for explicitly: "see all the tickets raised,
 * not by putting customer id". A real list/table (not another row of
 * colorful cards), click a row to open that ticket read-only.
 *
 * `scroll={{ x: 760 }}` makes the table scroll horizontally on a narrow
 * (phone-width) screen instead of squashing every column illegibly.
 */
function AllTicketsTable({ tickets, loading }) {
  const navigate = useNavigate();

  const columns = [
    { title: "Ticket", dataIndex: "ticket_id", key: "ticket_id", render: (id) => `#${id}` },
    { title: "Customer", dataIndex: "customer_id", key: "customer_id", render: (id) => `#${id}` },
    { title: "Order", dataIndex: "order_id", key: "order_id", render: (id) => `#${id}` },
    { title: "Status", dataIndex: "status", key: "status", render: (status) => <StatusPill status={status} /> },
    {
      title: "Last message",
      dataIndex: "last_message",
      key: "last_message",
      ellipsis: true,
      render: (text) => <Typography.Text type="secondary">{text || "—"}</Typography.Text>,
    },
    {
      title: "Opened",
      dataIndex: "created_date",
      key: "created_date",
      render: (value) => formatDateTime(value),
    },
  ];

  return (
    <Table
      rowKey="ticket_id"
      columns={columns}
      dataSource={tickets}
      loading={loading}
      pagination={{ pageSize: 10, hideOnSinglePage: true }}
      size="middle"
      scroll={{ x: 760 }}
      onRow={(record) => ({
        className: "qc-manager-row",
        onClick: () => navigate(config.ticketDetailPath(record.ticket_id)),
      })}
    />
  );
}

export default AllTicketsTable;
