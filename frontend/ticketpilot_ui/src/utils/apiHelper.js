import axios from "axios";
import config from "../data/config";

/**
 * Shared axios instance for every ticketpilot_das call. Every service
 * below uses `api`, not the bare `axios` import, so a support manager's
 * token attaches automatically to the approval_engine endpoints.
 */
const api = axios.create({ baseURL: config.API_BASE });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

/**
 * apiHelper.js is a plain module, not a React component -- it can't
 * dispatch() directly without importing the store, which would create a
 * circular import (store.js -> sessionSlice.js -> apiHelper.js ->
 * store.js). Firing a plain browser event and letting App.jsx (which
 * already owns dispatch) listen for it avoids that entirely.
 */
export const AUTH_EXPIRED_EVENT = "auth:expired";

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  },
);

/* ==================================================================
 * auth
 * ================================================================== */

export const loginService = async (email, password) => {
  const response = await api.post(`/auth/login`, { email, password });
  return response.data; // { access_token, user_id, role }
};

/* ==================================================================
 * ticket_management
 * ================================================================== */

// customer_id is deliberately not a parameter here anymore -- the backend
// derives it exclusively from the caller's JWT (see
// ticket_management.entity.PydanticModels.SubmitTicketRequest). orderId
// is optional; when omitted, the backend auto-picks the logged-in
// customer's own most recent order -- the SAME order the home-page
// status panel shows (see getMyOrderStatusService below), so the chat
// and the dashboard always agree on which order they're talking about.
// There used to be a scenarioId param here that made the backend raise
// the ticket against a different, scenario-specific order -- removed,
// since that could disagree with what the dashboard was showing. A
// scenario card's id no longer travels to the backend at all; only its
// canned message text does (see ScenarioPicker/scenarios.js).
export const submitTicketService = async (orderId, message) => {
  const response = await api.post(`/ticketmanagement/submitTicket`, {
    order_id: orderId,
    message,
  });
  return response.data;
};

export const reopenTicketService = async (ticketId, message) => {
  const response = await api.post(`/ticketmanagement/reopenTicket/${ticketId}`, { message });
  return response.data;
};

/**
 * Continues an EXISTING, still-open ticket -- this is what makes the
 * customer-facing conversation feel like one continuous chat thread
 * instead of a new ticket per message. The backend decides what to do
 * with it based on current status (re-run the agent if investigating /
 * awaiting_customer, just record it if escalated / pending_approval,
 * 400 if already resolved -- see ticket_management.db_operations.Ticket.send_message).
 */
export const sendMessageService = async (ticketId, message) => {
  const response = await api.post(`/ticketmanagement/sendMessage/${ticketId}`, { message });
  return response.data;
};

export const getTicketService = async (ticketId) => {
  const response = await api.get(`/ticketmanagement/getTicket/${ticketId}`);
  return response.data;
};

// No customer_id param anymore -- there's no way (and no reason) for the
// frontend to ask for "someone's" tickets by id; a logged-in customer's
// JWT already scopes this to their own, and a manager's JWT gets
// everyone's. Only the optional status filter remains.
// Backs the customer home page's live order-status panel -- the
// customer's own most recent order, OUTSIDE of any ticket/chat context,
// so "where's my order" doesn't require starting a conversation to ask.
// Returns { order: <snapshot> | null }; null means no orders yet.
export const getMyOrderStatusService = async () => {
  const response = await api.get(`/ticketmanagement/myOrderStatus`);
  return response.data;
};

export const getTicketsService = async (status) => {
  const params = {};
  if (status) params.status = status;
  const response = await api.get(`/ticketmanagement/getTickets`, { params });
  return response.data;
};

// Manager-only. Wipes every ticket/message/approval and re-times the two
// demo orders, by calling sp_reset_demo() server-side -- the same thing
// that used to require SSHing into the VM and running a mysql command by
// hand. Lets a manager reset the demo straight from the app, phone
// included. See ticket_management.routes.Ticket.reset_demo.
export const resetDemoService = async () => {
  const response = await api.post(`/ticketmanagement/resetDemo`);
  return response.data;
};

/* ==================================================================
 * approval_engine (support-manager only -- requires the JWT attached above)
 * ================================================================== */

export const getPendingApprovalsService = async () => {
  const response = await api.get(`/approvalengine/getPendingApprovals`);
  return response.data;
};

// courierConfirmed is only actually enforced server-side when the
// approval's order is already marked "delivered" (see
// approval_engine.db_operations.Approval.approve_action) -- for any
// other order status the backend ignores it and approves normally, so
// it's safe to always send whatever the checkbox's current value is.
export const approveActionService = async (approvalId, courierConfirmed) => {
  const response = await api.post(`/approvalengine/approveAction/${approvalId}`, {
    courier_confirmed: Boolean(courierConfirmed),
  });
  return response.data;
};

export const rejectActionService = async (approvalId, reason) => {
  const response = await api.post(`/approvalengine/rejectAction/${approvalId}`, { reason });
  return response.data;
};
