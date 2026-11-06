/**
 * Demo scenario cards for the logged-in customer's "Get Help" drawer --
 * a quick-reply-style shortcut so a demo viewer doesn't have to type
 * their own opening message. Each card ONLY supplies realistic message
 * text -- the `id` below no longer selects or creates a different
 * order on the backend (that used to be the case; removed, because it
 * let the chat describe a different order than the one the customer's
 * home-page status panel was showing). Whichever card is clicked, the
 * ticket is raised against whoever is actually logged in's own one
 * real order (see ticket_management.db_operations.Ticket.submit_ticket).
 *
 * Every scenario here is a REAL delivery-app support contact reason,
 * picked because the backend can genuinely act on it -- not a generic
 * chat-starter. Deliberately NOT included: a menu/dietary question (no
 * knowledge-base coverage exists for it, and this is a support bot, not
 * a chat assistant), "what was in my last order" (not a real support
 * contact reason), and a billing/double-charge dispute (no payment-
 * system tool exists, so there would be nothing for the agent to check
 * -- that one is correctly a pure human escalation, not a demo of the
 * agent "handling" anything).
 *
 * Two of these (missing-item, order-cancelled) rely on knowledge-base
 * articles added via add_kb_articles.sql -- without that script having
 * been run (and the embedding script re-run after it), the agent will
 * correctly say it doesn't have specific information rather than
 * fabricate a policy.
 */
const SCENARIOS = [
  {
    id: "late-order",
    icon: "delivery",
    title: "My order hasn't arrived",
    subtitle: "It's past the expected delivery time",
    message: "My order hasn't shown up yet and I think it's running late.",
  },
  {
    id: "not-received",
    icon: "alert",
    title: "It shows delivered, but I didn't get it",
    subtitle: "Order status says delivered",
    message: "My order is marked as delivered, but I never actually received it.",
  },
  {
    id: "missing-item",
    icon: "order",
    title: "An item is missing or wrong",
    subtitle: "Something in my order isn't right",
    message: "Part of my order is missing, or I got the wrong item -- can you help?",
  },
  {
    id: "order-cancelled",
    icon: "store",
    title: "My order was cancelled",
    subtitle: "The restaurant couldn't fulfill it",
    message: "My order seems to have been cancelled -- do I get a refund?",
  },
  {
    id: "late-quality",
    icon: "delivery",
    title: "My order arrived very late",
    subtitle: "It was delivered well past the ETA",
    message: "My order finally arrived, but it was delivered way later than expected.",
  },
  {
    id: "track-order",
    icon: "track",
    title: "Track my order",
    subtitle: "Check the live status of my order",
    message: "Can you tell me the current status of my order?",
  },
  {
    id: "cancel-change",
    icon: "cancel",
    title: "Cancel or change my order",
    subtitle: "Is it too late to update it?",
    message: "I'd like to cancel or change my order -- is that still possible?",
  },
  {
    id: "refund-timing",
    icon: "billing",
    title: "When will I get my refund?",
    subtitle: "Checking on a refund that's already approved",
    message: "I'm waiting on a refund -- how long does that usually take?",
  },
];

export default SCENARIOS;
