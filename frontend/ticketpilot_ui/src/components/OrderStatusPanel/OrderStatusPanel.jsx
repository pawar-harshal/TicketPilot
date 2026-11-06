import { useEffect, useState } from "react";
import { Card, Skeleton, Typography } from "antd";

import { getMyOrderStatusService } from "../../utils/apiHelper";
import { DeliveryIcon } from "../IssueIcons/IssueIcons";
import styles from "./OrderStatusPanel.module.css";

const titleCase = (s) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// Where the van sits on the route line for each status -- out of 100,
// matched to the three waypoint dots below (0 / 50 / 100). Cancelled
// doesn't move along this at all (see the dedicated cancelled render).
const PROGRESS_BY_STATUS = {
  placed: 4,
  out_for_delivery: 50,
  delivered: 100,
};

/**
 * Live order-status panel for the customer's home page (SubmitTicket.jsx)
 * -- sits to the LEFT of "Get Help" so a customer who just wants to know
 * "where's my order" can see it at a glance, outside of and separate
 * from the chat, instead of that question getting mixed up with
 * whatever else the support agent's replies are about.
 *
 * Shows the customer's own most recent order (same default
 * submit_ticket already uses -- see getMyOrderStatus on the backend)
 * via a small always-on route animation: a van icon travels along a
 * dashed line through Placed -> On the way -> Delivered. Cancelled
 * orders get their own static, greyed-out treatment instead of a route.
 *
 * Pure CSS/SVG -- no shader, no canvas -- cheap enough to just always be
 * running in the background of the page.
 */
function OrderStatusPanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [order, setOrder] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getMyOrderStatusService()
      .then((data) => {
        if (!cancelled) setOrder(data.order);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load your order status right now.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <Card className={styles.panel}>
        <Skeleton active paragraph={{ rows: 3 }} />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={styles.panel}>
        <Typography.Text type="secondary">{error}</Typography.Text>
      </Card>
    );
  }

  if (!order) {
    return (
      <Card className={styles.panel}>
        <Typography.Text type="secondary">You don't have any orders yet.</Typography.Text>
      </Card>
    );
  }

  const isCancelled = order.status === "cancelled";
  const progress = PROGRESS_BY_STATUS[order.status] ?? 0;
  const itemsLabel = (order.items || [])
    .map((i) => `${i.name}${i.qty > 1 ? ` x${i.qty}` : ""}`)
    .join(", ");

  return (
    <Card className={styles.panel}>
      <div className={styles.headerRow}>
        <span className={styles.orderLabel}>Order #{order.order_id}</span>
        <span className={isCancelled ? styles.statusPillCancelled : styles.statusPill}>
          {titleCase(order.status)}
        </span>
      </div>

      <div className={styles.items}>{itemsLabel || "—"}</div>
      <div className={styles.total}>
        {order.currency} {Number(order.total_amount).toFixed(2)}
      </div>

      {order.is_late && !isCancelled && (
        <div className={styles.lateNote}>Running {order.minutes_late} min late</div>
      )}

      {isCancelled ? (
        <div className={styles.routeCancelled}>
          <div className={styles.routeLineCancelled} />
          <div className={styles.cancelledBadge}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </div>
          <span className={styles.cancelledLabel}>This order was cancelled</span>
        </div>
      ) : (
        <div className={styles.route}>
          <div className={styles.routeTrack}>
            <div className={styles.routeLine} />
            <div className={styles.routeLineFill} style={{ width: `${progress}%` }} />
            <div className={`${styles.waypoint} ${styles.waypointStart} ${progress >= 4 ? styles.waypointDone : ""}`} />
            <div className={`${styles.waypoint} ${styles.waypointMid} ${progress >= 50 ? styles.waypointDone : ""}`} />
            <div className={`${styles.waypoint} ${styles.waypointEnd} ${progress >= 100 ? styles.waypointDone : ""}`} />
            <div
              className={`${styles.van} ${order.status === "out_for_delivery" ? styles.vanDriving : ""} ${order.status === "placed" ? styles.vanIdle : ""}`}
              style={{ left: `${progress}%` }}
            >
              <DeliveryIcon width={22} height={22} />
            </div>
          </div>
          <div className={styles.routeLabels}>
            <span>Placed</span>
            <span>On the way</span>
            <span>Delivered</span>
          </div>
        </div>
      )}
    </Card>
  );
}

export default OrderStatusPanel;
