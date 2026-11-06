import { createSlice } from "@reduxjs/toolkit";

const STORAGE_KEY = "themeMode";

const getInitialMode = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // localStorage can throw in some contexts -- fall back to the default below.
  }
  // No saved preference yet (first visit, or storage unavailable) -- default
  // to dark, matching the app's "AI agent" visual identity (the Silk shader
  // background etc. were designed dark-first). A visitor who explicitly
  // toggles to light still gets that remembered via STORAGE_KEY above.
  return "dark";
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
