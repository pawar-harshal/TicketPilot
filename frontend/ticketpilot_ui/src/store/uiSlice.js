import { createSlice } from "@reduxjs/toolkit";

const STORAGE_KEY = "themeMode";

const getInitialMode = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // localStorage can throw in some contexts -- fall back to light.
  }
  return "light";
};

const uiSlice = createSlice({
  name: "ui",
  initialState: {
    mode: getInitialMode(), // "light" | "dark"
  },
  reducers: {
    toggleTheme: (state) => {
      state.mode = state.mode === "light" ? "dark" : "light";
      try {
        localStorage.setItem(STORAGE_KEY, state.mode);
      } catch {
        // ignore -- per-viewer convenience only
      }
    },
  },
});

export const { toggleTheme } = uiSlice.actions;
export default uiSlice.reducer;
