import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  approveActionService,
  getPendingApprovalsService,
  rejectActionService,
} from "../utils/apiHelper";

export const fetchPendingApprovals = createAsyncThunk(
  "approvals/fetchPendingApprovals",
  async () => getPendingApprovalsService(),
);

export const approveAction = createAsyncThunk(
  "approvals/approveAction",
  async ({ approvalId, courierConfirmed } = {}) => approveActionService(approvalId, courierConfirmed),
);

export const rejectAction = createAsyncThunk(
  "approvals/rejectAction",
  async ({ approvalId, reason }) => rejectActionService(approvalId, reason),
);

const approvalSlice = createSlice({
  name: "approvals",
  initialState: {
    pending: [],
    status: "idle",
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchPendingApprovals.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchPendingApprovals.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.pending = action.payload;
      })
      .addCase(fetchPendingApprovals.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error?.message || "Could not load approvals.";
      })
      // Approve/reject both remove the actioned approval from the local
      // queue immediately -- no need to wait for a full re-fetch.
      .addCase(approveAction.fulfilled, (state, action) => {
        state.pending = state.pending.filter((a) => a.approval_id !== action.payload.approval_id);
      })
      .addCase(rejectAction.fulfilled, (state, action) => {
        state.pending = state.pending.filter((a) => a.approval_id !== action.payload.approval_id);
      });
  },
});

export default approvalSlice.reducer;
