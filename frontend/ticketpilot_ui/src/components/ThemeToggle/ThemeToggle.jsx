import { Button, Tooltip } from "antd";
import { useDispatch, useSelector } from "react-redux";

import { toggleTheme } from "../../store/uiSlice";
import styles from "./ThemeToggle.module.css";

/**
 * Sun/moon icon, same convention most sites use for a light/dark switch
 * (plain line icons rather than antd's light-bulb preset, which read as
 * "idea" rather than "theme"). Plain inline SVG, stroke = currentColor,
 * so it always matches the button's own text color in both themes.
 */
function SunIcon(props) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="4.5" />
      <path d="M12 2.5v3M12 18.5v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2.5 12h3M18.5 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
    </svg>
  );
}

function MoonIcon(props) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
    </svg>
  );
}

/**
 * Light/dark toggle, meant to sit top-right on every header (customer
 * BrandBar, the manager AppLayout, Landing and Login alike). Persisted
 * via uiSlice to localStorage so it survives a refresh.
 */
function ThemeToggle() {
  const dispatch = useDispatch();
  const mode = useSelector((state) => state.ui.mode);
  const isDark = mode === "dark";

  return (
    <Tooltip title={isDark ? "Switch to light mode" : "Switch to dark mode"}>
      <Button
        shape="circle"
        className={styles.toggle}
        icon={isDark ? <MoonIcon className={styles.icon} /> : <SunIcon className={styles.icon} />}
        onClick={() => dispatch(toggleTheme())}
      />
    </Tooltip>
  );
}

export default ThemeToggle;
