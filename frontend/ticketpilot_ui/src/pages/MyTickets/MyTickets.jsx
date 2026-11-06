import { useEffect } from "react";
import { Empty, Typography } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { Link } from "react-router-dom";

import config from "../../data/config";
import { fetchTickets } from "../../store/ticketSlice";
import TicketSummaryCard from "../../components/TicketSummaryCard/TicketSummaryCard";
import BrandBar from "../../components/BrandBar/BrandBar";

/**
 * No more "type your customer ID" box -- that was a leftover from before
 * customer login existed, and asked a real customer for plumbing they'd
 * never know. This page is behind RequireCustomerAuth now, so the
 * logged-in customer's own tickets just load automatically, scoped
 * server-side to their JWT (see getTickets in ticket_management/routes).
 */
function MyTickets() {
  const dispatch = useDispatch();
  const { list, status } = useSelector((state) => state.tickets);

  useEffect(() => {
    dispatch(fetchTickets());
  }, [dispatch]);

  return (
    <>
      <BrandBar />
      <div className="page-shell">
        <Typography.Title level={3}>My Tickets</Typography.Title>

        {status === "succeeded" && list.length === 0 && (
          <Empty description="You don't have any tickets yet." />
        )}

        {list.map((ticket) => (
          <TicketSummaryCard key={ticket.ticket_id} ticket={ticket} />
        ))}

        <Typography.Paragraph style={{ marginTop: 16 }}>
          <Link to={config.routes.submitTicket}>Submit a new ticket</Link>
        </Typography.Paragraph>
      </div>
    </>
  );
}

export default MyTickets;
