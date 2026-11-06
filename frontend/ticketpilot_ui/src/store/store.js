import { configureStore } from "@reduxjs/toolkit";
import sessionReducer from "./sessionSlice";
import ticketsReducer from "./ticketSlice";
import approvalsReducer from "./approvalSlice";
import uiReducer from "./uiSlice";

export const store = configureStore({
  reducer: {
    session: sessionReducer,
    tickets: ticketsReducer,
    approvals: approvalsReducer,
    ui: uiReducer,
  },
});
