import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Provider, useSelector } from "react-redux";
import { ConfigProvider, theme as antdTheme } from "antd";

import App from "./App";
import { store } from "./store/store";

import "antd/dist/reset.css";
import "./index.css";

// Deep indigo/purple palette, lifted from the landing page's Silk shader
// background (#02010A -> #04052E -> #3D2C8D -> #916BBF) so the rest of the
// app reads as one consistent, "AI agent" visual identity instead of a
// marketing page bolted onto an unrelated product theme. One accent color,
// reused (lighter/darker) across both light and dark mode rather than a
// different hue per status.
const LIGHT_TOKEN = {
  colorPrimary: "#3D2C8D",
  colorInfo: "#3D2C8D",
  borderRadius: 10,
  fontFamily:
    "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
};

const DARK_TOKEN = {
  ...LIGHT_TOKEN,
  colorPrimary: "#916BBF",
  colorInfo: "#916BBF",
  colorBgBase: "#07051a",
  colorTextBase: "#ece9f5",
};

const COMPONENT_TOKENS = {
  Button: { borderRadius: 10, controlHeight: 38 },
  Card: { borderRadiusLG: 16 },
  Input: { borderRadius: 10 },
};

/**
 * Reads the persisted theme mode (uiSlice) and drives three things from
 * one source of truth: antd's own ConfigProvider theme (so antd's
 * internals -- Card, Input, Table, etc. -- repaint themselves), the
 * `data-theme` attribute on <html> (so our own CSS variables in
 * index.css switch), and keeping the two in sync on every toggle.
 */
function ThemedApp() {
  const mode = useSelector((state) => state.ui.mode);

  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", mode);
  }

  const theme = {
    algorithm: mode === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
    token: mode === "dark" ? DARK_TOKEN : LIGHT_TOKEN,
    components: COMPONENT_TOKENS,
  };

  return (
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <ThemedApp />
  </Provider>,
);
