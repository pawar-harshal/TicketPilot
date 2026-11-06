// Routes

const routes = {
  landing: "/",
  submitTicket: "/support",
  myTickets: "/my-tickets",
  ticketDetail: "/tickets/:ticketId",
  login: "/login",
  approvalQueue: "/approvals",
  profile: "/profile",
};

// Build a concrete ticketDetail path for a given id -- routes.ticketDetail
// above stays the react-router pattern.
const ticketDetailPath = (ticketId) => `/tickets/${ticketId}`;

const config = {
  appTitle: "TicketPilot | QuickCrave",
  platformName: "TicketPilot",
  clientName: "QuickCrave",

  // Base URL for ticketpilot_das. Point this at wherever main.py is
  // running (see backend/README.md).
  API_BASE: import.meta.env.VITE_API_BASE || "http://localhost:8000",

  routes,
  ticketDetailPath,

  // How long a support-manager login stays valid client-side before a
  // silent re-check kicks in -- mirrors the backend's jwt_expiry_minutes
  // in config.ini, just expressed in days for getExpireAt().
  sessionExpiryTimeInDays: 0.33, // ~8 hours, matches the default jwt_expiry_minutes=480
};

export default config;
