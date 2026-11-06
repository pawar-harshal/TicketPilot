import config from "../data/config";

/**
 * Returns a future timestamp (ms) based on config.sessionExpiryTimeInDays.
 * Used to stamp a support-manager session so we know when to force a
 * re-login, same pattern as the reference app's sessionSlice.
 */
export const getExpireAt = () =>
  Date.now() + config.sessionExpiryTimeInDays * 24 * 60 * 60 * 1000;

export const formatDateTime = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const datePart = date.toLocaleDateString("en-US", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const timePart = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${datePart}, ${timePart}`;
};

export const STATUS_LABELS = {
  investigating: "Investigating",
  awaiting_customer: "Waiting on you",
  resolved: "Resolved",
  escalated: "Escalated to support",
  pending_approval: "Awaiting approval",
};

// Muted dot colors for StatusPill -- deliberately desaturated (no bright
// antd preset Tag colors like "red"/"gold"/"success"), so the manager
// dashboard and the customer chat both read as calm, not colorful. Kept
// as hex values (not antd color names) since they're used as inline
// `background` on a plain <span>, not an antd <Tag>.
export const STATUS_TONE = {
  investigating: "#8a94a0",
  awaiting_customer: "#5b7fa6",
  resolved: "#4f9d69",
  escalated: "#c08a3e",
  pending_approval: "#a6673e",
};

export const APPROVAL_STATUS_LABELS = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
};
