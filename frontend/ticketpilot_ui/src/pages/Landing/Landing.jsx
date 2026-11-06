import { Button, Typography } from "antd";
import { Link } from "react-router-dom";
import { useSelector } from "react-redux";

import config from "../../data/config";
import Logo from "../../components/Logo/Logo";
import ThemeToggle from "../../components/ThemeToggle/ThemeToggle";
import SilkBackground from "../../components/SilkBackground/SilkBackground";
import styles from "./Landing.module.css";

/**
 * Public entry point. No longer guarded away from a logged-in session
 * (see App.jsx) -- it's a normal public page, so someone who's already
 * logged in can land here too (a shared link, hitting "/" directly,
 * etc.) and the topbar button adapts to that instead of always sending
 * them to /login.
 *
 * Text hierarchy: a small uppercase eyebrow label, then a large, bold,
 * uppercase headline, then one supporting line. The right side is a
 * circular, glowing "orb" rendering of the Silk shader rather than a
 * rectangular panel, meant to read as a stand-in for the AI agent
 * itself.
 */
function Landing() {
  const session = useSelector((state) => state.session.user);

  const ctaTo = session
    ? session.role === "support_manager"
      ? config.routes.approvalQueue
      : config.routes.submitTicket
    : config.routes.login;
  const ctaLabel = session ? "Go to dashboard" : "Log in";

  return (
    <div className={styles.page}>
      <div className={styles.topbar}>
        <Logo size={30} />
        <div className={styles.brand}>{config.platformName}</div>
        <div className="qc-flex-spacer" />
        <div className={styles.actions}>
          <ThemeToggle />
          <Link to={ctaTo}>
            <Button type="primary">{ctaLabel}</Button>
          </Link>
        </div>
      </div>

      <div className={styles.hero}>
        <div className={styles.left}>
          <span className={styles.eyebrow}>
            <span className={styles.eyebrowDot} />
            AI Support Agent
          </span>
          <Typography.Title level={1} className={styles.tagline}>
            Support that actually checks the facts
          </Typography.Title>
          <Typography.Paragraph type="secondary" className={styles.description}>
            {config.platformName} looks up your order's real status before it ever replies to you.
          </Typography.Paragraph>
        </div>

        <div className={styles.right}>
          <div className={styles.orbStage}>
            <div className={styles.orbGlow} />
            <div className={styles.orb}>
              <SilkBackground />
            </div>
            <span className={styles.caption}>Meet your AI support agent</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
