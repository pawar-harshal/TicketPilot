import { STATUS_LABELS, STATUS_TONE } from "../../utils/helper";

/**
 * One consistent, muted way to show a ticket's status everywhere --
 * chat header, ticket lists, approval queue, manager's all-tickets list.
 * Replaces antd's bright preset Tag colors (the "too many colors"
 * complaint) with a neutral pill + a single small colored dot.
 */
function StatusPill({ status }) {
  return (
    <span className="status-pill">
      <span className="status-pill__dot" style={{ background: STATUS_TONE[status] || "#9a9490" }} />
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export default StatusPill;
