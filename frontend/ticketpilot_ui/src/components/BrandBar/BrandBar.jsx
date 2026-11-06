import config from "../../data/config";
import Logo from "../Logo/Logo";
import ThemeToggle from "../ThemeToggle/ThemeToggle";
import ProfileMenu from "../ProfileMenu/ProfileMenu";
import styles from "./BrandBar.module.css";

/**
 * Thin branded header for every customer-facing page (SubmitTicket,
 * MyTickets, TicketDetail) -- keeps QuickCrave's identity visible the
 * way Swiggy/Zomato always keep their own brand bar above a support
 * chat. These pages are all behind RequireCustomerAuth now, so a
 * session is always present here -- account + logout now live in the
 * ProfileMenu dropdown rather than a standing "Hi, X" greeting and a
 * separate logout button.
 */
function BrandBar() {
  return (
    <div className={styles.bar}>
      <Logo />
      <div>
        <div className={styles.name}>{config.clientName}</div>
        <div className={styles.tagline}>Support, powered by {config.platformName}</div>
      </div>
      <div className="qc-flex-spacer" />
      <div className={styles.actions}>
        <ThemeToggle />
        <ProfileMenu />
      </div>
    </div>
  );
}

export default BrandBar;
