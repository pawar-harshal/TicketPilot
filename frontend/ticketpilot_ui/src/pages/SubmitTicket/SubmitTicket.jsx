import { useEffect, useState } from "react";
import { Alert, Button, Card, Drawer, Form, Input, Typography } from "antd";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

import config from "../../data/config";
import { fetchTickets, submitTicket } from "../../store/ticketSlice";
import BrandBar from "../../components/BrandBar/BrandBar";
import ScenarioPicker from "../../components/ScenarioPicker/ScenarioPicker";
import TicketMessageThread from "../../components/TicketMessageThread/TicketMessageThread";
import Logo from "../../components/Logo/Logo";
import OrderStatusPanel from "../../components/OrderStatusPanel/OrderStatusPanel";
import StatusPill from "../../components/StatusPill/StatusPill";
import { HelpIcon, ChevronRightIcon } from "../../components/IssueIcons/IssueIcons";
import styles from "./SubmitTicket.module.css";

/**
 * Entry point for a logged-in customer. Two columns below the greeting:
 * the LEFT column is a live, always-visible order-status panel
 * (OrderStatusPanel) -- outside of and separate from any chat, so a
 * customer who just wants to know "where's my order" gets a real
 * answer at a glance instead of that question getting mixed up with
 * whatever an agent reply happens to be about. The RIGHT column is the
 * single "Get Help" card -- tapping it opens a bottom sheet listing
 * issue categories (ScenarioPicker) plus a free-text fallback, the same
 * pattern a real delivery app's help center uses: one clear entry
 * point, then a sheet of real options, rather than every option dumped
 * on the page at once. Columns stack (status above help) on narrow
 * screens.
 *
 * No "view my tickets" link here anymore -- that's a separate feature,
 * not part of the "get help" flow, and was adding a second navigation
 * option where there should just be one clear action.
 *
 * Neither path asks for a customer_id or order_id anymore -- that
 * plumbing is gone. Identity comes exclusively from the session (this
 * page is behind RequireCustomerAuth), and the backend auto-picks the
 * logged-in customer's own most recent order when none is given (see
 * ticket_management.db_operations.Ticket.submit_ticket) -- the exact
 * same order OrderStatusPanel shows. A scenario card no longer causes a
 * different order to be used; it only supplies canned message text.
 *
 * While the ticket is being created, we don't just show a spinner on the
 * row -- we swap the whole page for a live-looking chat preview with the
 * customer's own message already in it (pendingPreview), so it genuinely
 * feels like the chat opened immediately. The real TicketDetail page
 * (reached once submitTicket resolves) renders the identical message, so
 * there's no visual jump when we navigate there.
 *
 * The Get Help drawer also surfaces the customer's own ticket history
 * (fetchTickets -- already returns ticket_id/status/last_message/created_date
 * for all of this customer's tickets, no new endpoint needed): their one
 * currently-open ticket, if any, at the top -- clicking it jumps straight
 * into that conversation -- followed by their past resolved tickets. This
 * is purely a "jump back in" convenience; the actual no-duplicate-tickets
 * behavior (picking a scenario card while one ticket is already open
 * continues THAT ticket instead of creating a new one) is enforced
 * backend-side in submit_ticket/get_open_ticket_for_order, so it holds
 * even if a customer never opens this list.
 */
function SubmitTicket() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const session = useSelector((state) => state.session.user);
  const { list: tickets } = useSelector((state) => state.tickets);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [loadingScenarioId, setLoadingScenarioId] = useState(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [pendingPreview, setPendingPreview] = useState(null); // { message }

  // Loaded once up front (not just when the drawer opens) so the "Get
  // Help" entry itself could eventually reflect it too, and so there's no
  // flash of an empty list the first time the drawer is opened.
  useEffect(() => {
    dispatch(fetchTickets());
  }, [dispatch]);

  const activeTicket = tickets.find((t) => t.status !== "resolved");
  const resolvedTickets = tickets.filter((t) => t.status === "resolved");

  const goToExistingTicket = (ticketId) => {
    closeHelp();
    navigate(config.ticketDetailPath(ticketId));
  };

  const goToTicket = async (message) => {
    const ticket = await dispatch(submitTicket({ message })).unwrap();
    navigate(config.ticketDetailPath(ticket.ticket_id));
  };

  const closeHelp = () => {
    setHelpOpen(false);
    setShowCustomForm(false);
  };

  const handlePickScenario = async (scenario) => {
    setError(null);
    setLoadingScenarioId(scenario.id);
    setPendingPreview({ message: scenario.message });
    try {
      // Only the scenario's canned message text goes to the backend --
      // the scenario id itself no longer picks or creates a different
      // order. Every ticket (whichever card was clicked, or the
      // free-text form below) is raised against the customer's own one
      // real order, the SAME one OrderStatusPanel is already showing,
      // so the chat and the dashboard never disagree about which order
      // they're talking about.
      await goToTicket(scenario.message);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not start this conversation. Please try again.");
      setPendingPreview(null);
    } finally {
      setLoadingScenarioId(null);
    }
  };

  const onFinish = async (values) => {
    setError(null);
    setSubmitting(true);
    setPendingPreview({ message: values.message });
    try {
      await goToTicket(values.message);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not submit your ticket. Please try again.");
      setPendingPreview(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (pendingPreview) {
    return (
      <>
        <BrandBar />
        <div className="page-shell" style={{ maxWidth: 640 }}>
          <div className="chat-header">
            <div className="chat-header__avatar">
              <Logo size={26} />
            </div>
            <div className="chat-header__info">
              <div className="chat-header__name">TicketPilot Agent</div>
              <div className="chat-header__status">Starting your conversation…</div>
            </div>
          </div>
          <Card className="chat-card" bodyStyle={{ padding: "12px 16px" }}>
            <TicketMessageThread
              messages={[{ sender: "customer", message: pendingPreview.message, created_date: new Date().toISOString() }]}
              typing
            />
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <BrandBar />
      <div className="page-shell" style={{ maxWidth: 760 }}>
        <div className={styles.hero}>
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            {session?.name ? `How can we help, ${session.name}?` : "How can we help?"}
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            Tell us what's going on with an order, and we'll bring up the right conversation right away.
          </Typography.Paragraph>
        </div>

        {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}

        <div className={styles.columns}>
          <div className={styles.leftCol}>
            <OrderStatusPanel />
          </div>

          <div className={styles.rightCol}>
            <Card className={styles.helpEntry} onClick={() => setHelpOpen(true)} role="button" tabIndex={0}>
              <div className={styles.helpEntryIcon}>
                <HelpIcon width={26} height={26} />
              </div>
              <div className={styles.helpEntryBody}>
                <span className={styles.helpEntryTitle}>Get Help</span>
                <div className={styles.helpEntrySubtitle}>Report an issue or ask a question about your order</div>
              </div>
              <ChevronRightIcon className={styles.helpEntryChevron} />
            </Card>
          </div>
        </div>
      </div>

      <Drawer
        title="What's going on?"
        placement="bottom"
        height="auto"
        open={helpOpen}
        onClose={closeHelp}
        styles={{
          content: { borderRadius: "20px 20px 0 0", maxHeight: "85vh" },
          body: { paddingBottom: 28 },
        }}
      >
        {(activeTicket || resolvedTickets.length > 0) && (
          <div className={styles.existingTickets}>
            {activeTicket && (
              <div
                className={styles.ticketRow}
                role="button"
                tabIndex={0}
                onClick={() => goToExistingTicket(activeTicket.ticket_id)}
              >
                <div className={styles.ticketRowInfo}>
                  <span className={styles.ticketRowTitle}>Ticket #{activeTicket.ticket_id} &middot; Active</span>
                  <span className={styles.ticketRowSubtitle}>{activeTicket.last_message}</span>
                </div>
                <StatusPill status={activeTicket.status} />
              </div>
            )}

            {resolvedTickets.length > 0 && (
              <div className={styles.resolvedList}>
                <Typography.Text type="secondary" className={styles.resolvedListLabel}>
                  Past tickets
                </Typography.Text>
                {resolvedTickets.map((t) => (
                  <div
                    key={t.ticket_id}
                    className={styles.ticketRow}
                    role="button"
                    tabIndex={0}
                    onClick={() => goToExistingTicket(t.ticket_id)}
                  >
                    <div className={styles.ticketRowInfo}>
                      <span className={styles.ticketRowTitle}>Ticket #{t.ticket_id}</span>
                      <span className={styles.ticketRowSubtitle}>{t.last_message}</span>
                    </div>
                    <StatusPill status={t.status} />
                  </div>
                ))}
              </div>
            )}

            {activeTicket && (
              <Typography.Text type="secondary" className={styles.existingTicketsHint}>
                You already have an open conversation -- picking an issue below will continue it instead of
                starting a new one.
              </Typography.Text>
            )}
          </div>
        )}

        <ScenarioPicker onPick={handlePickScenario} loadingId={loadingScenarioId} />

        <div style={{ textAlign: "center", marginTop: 16 }}>
          <Typography.Link onClick={() => setShowCustomForm((v) => !v)}>
            {showCustomForm ? "Hide" : "Describe something else"}
          </Typography.Link>
        </div>

        {showCustomForm && (
          <Form layout="vertical" onFinish={onFinish} style={{ marginTop: 16 }}>
            <Form.Item name="message" label="What happened?" rules={[{ required: true }]}>
              <Input.TextArea rows={4} placeholder="e.g. My order hasn't arrived and it's way past the delivery time." />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} block>
              Chat with support
            </Button>
          </Form>
        )}
      </Drawer>
    </>
  );
}

export default SubmitTicket;
