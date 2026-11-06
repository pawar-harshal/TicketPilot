import { createSlice } from "@reduxjs/toolkit";
import { getExpireAt } from "../utils/helper";

const initialState = {
  user: null,
  loaded: false,
};

const sessionSlice = createSlice({
  name: "session",
  initialState,
  reducers: {
    setSession: (state, action) => {
      if (!action.payload) return;

      const session = {
        ...action.payload,
        expiresAt: getExpireAt(),
      };

      state.user = session;
      localStorage.setItem("session", JSON.stringify(session));

      // apiHelper.js's axios interceptor reads this specific key on every
      // authenticated call -- session.accessToken alone (inside the
      // "session" blob above) is NOT what it looks at.
      if (session.accessToken) {
        localStorage.setItem("accessToken", session.accessToken);
      }
    },

    clearSession: (state) => {
      state.user = null;
      localStorage.removeItem("session");
      localStorage.removeItem("accessToken");
    },

    loadSession: (state) => {
      try {
        const saved = localStorage.getItem("session");

        if (saved) {
          const session = JSON.parse(saved);

          if (session && Date.now() < session?.expiresAt) {
            state.user = session;
          } else {
            localStorage.removeItem("session");
            localStorage.removeItem("accessToken");
            state.user = null;
          }
        }
      } catch (error) {
        console.error("Invalid session data in storage:", error);
        localStorage.removeItem("session");
        state.user = null;
      }

      state.loaded = true;
    },
  },
});

export const { setSession, clearSession, loadSession } = sessionSlice.actions;
export default sessionSlice.reducer;
