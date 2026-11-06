import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  getTicketService,
  getTicketsService,
  reopenTicketService,
  sendMessageService,
  submitTicketService,
} from "../utils/apiHelper";

export const submitTicket = createAsyncThunk(
  "tickets/submitTicket",
  async ({ orderId, message }) => submitTicketService(orderId, message),
);

export const reopenTicket = createAsyncThunk(
  "tickets/reopenTicket",
  async ({ ticketId, message }) => reopenTicketService(ticketId, message),
);

// The everyday "type a message and send it" action for an already-open
// conversation -- unlike submitTicket (always a NEW ticket) and
// reopenTicket (only for an already-resolved one), this continues
// whichever ticket is already open.
export const sendMessage = createAsyncThunk(
  "tickets/sendMessage",
  async ({ ticketId, message }) => sendMessageService(ticketId, message),
);

export const fetchTicket = createAsyncThunk(
  "tickets/fetchTicket",
  async (ticketId) => getTicketService(ticketId),
);

// Used by MyTickets -- no id to pass anymore, the logged-in customer's
// own tickets come back automatically based on their JWT.
export const fetchTickets = createAsyncThunk(
  "tickets/fetchTickets",
  async ({ status } = {}) => getTicketsService(status),
);

// Separate from `list` (the customer's own "My Tickets" results) so the
// support-manager dashboard's escalated-tickets panel doesn't clobber
// whatever a customer last searched for in the same browser tab.
export const fetchEscalatedTickets = createAsyncThunk(
  "tickets/fetchEscalatedTickets",
  async () => getTicketsService("escalated"),
);

// Every ticket, across every customer -- the manager's "All Tickets"
// list. Backend requires a logged-in manager JWT for this; apiHelper's
// axios instance already attaches it automatically whenever one is in
// localStorage.
export const fetchAllTickets = createAsyncThunk(
  "tickets/fetchAllTickets",
  async () => getTicketsService(undefined),
);

const ticketSlice = createSlice({
  name: "tickets",
  initialState: {
    currentTicket: null,
    list: [],
    escalated: [],
    escalatedStatus: "idle",
    all: [],
    allStatus: "idle",
    status: "idle", // idle | loading | succeeded | failed
    error: null,
  },
  reducers: {
    clearCurrentTicket: (state) => {
      state.currentTicket = null;
    },
    // Shows the customer's own message in the thread the instant they hit
    // send, instead of waiting for the full round trip (which includes the
    // agent's turn and can take a few seconds) to come back. Flagged
    // `_optimistic` so a failed send can be cleanly rolled back; a
    // successful one is simply replaced wholesale by the real ticket the
    // server returns (see sendMessage.fulfilled / reopenTicket.fulfilled).
    appendOptimisticMessage: (state, action) => {
      if (!state.currentTicket) return;
      state.currentTicket.messages = [
        ...(state.currentTicket.messages || []),
        {
          sender: "customer",
          message: action.payload.message,
          created_date: new Date().toISOString(),
          _optimistic: true,
        },
      ];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitTicket.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(submitTicket.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.currentTicket = action.payload;
      })
      .addCase(submitTicket.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not submit ticket.";
      })
      .addCase(reopenTicket.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(reopenTicket.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.currentTicket = action.payload;
      })
      .addCase(reopenTicket.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not reopen ticket.";
        if (state.currentTicket) {
          state.currentTicket.messages = (state.currentTicket.messages || []).filter((m) => !m._optimistic);
        }
      })
      .addCase(fetchTicket.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchTicket.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.currentTicket = action.payload;
      })
      .addCase(fetchTicket.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not load ticket.";
      })
      .addCase(fetchTickets.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchTickets.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.list = action.payload;
      })
      .addCase(fetchTickets.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not load tickets.";
      })
      .addCase(sendMessage.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.currentTicket = action.payload;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not send your message.";
        if (state.currentTicket) {
          state.currentTicket.messages = (state.currentTicket.messages || []).filter((m) => !m._optimistic);
        }
      })
      .addCase(fetchEscalatedTickets.pending, (state) => {
        state.escalatedStatus = "loading";
      })
      .addCase(fetchEscalatedTickets.fulfilled, (state, action) => {
        state.escalatedStatus = "succeeded";
        state.escalated = action.payload;
      })
      .addCase(fetchEscalatedTickets.rejected, (state) => {
        state.escalatedStatus = "failed";
      })
      .addCase(fetchAllTickets.pending, (state) => {
        state.allStatus = "loading";
      })
      .addCase(fetchAllTickets.fulfilled, (state, action) => {
        state.allStatus = "succeeded";
        state.all = action.payload;
      })
      .addCase(fetchAllTickets.rejected, (state) => {
        state.allStatus = "failed";
      });
  },
});

export const { clearCurrentTicket, appendOptimisticMessage } = ticketSlice.actions;
export default ticketSlice.reducer;
