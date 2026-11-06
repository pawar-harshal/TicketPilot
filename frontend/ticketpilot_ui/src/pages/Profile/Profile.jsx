import { useState } from "react";
import { Avatar, Button, Card, Divider, Input, message, Popconfirm, Typography } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import config from "../../data/config";
import Logo from "../../components/Logo/Logo";
import ThemeToggle from "../../components/ThemeToggle/ThemeToggle";
import { resetDemoService } from "../../utils/apiHelper";
import styles from "./Profile.module.css";

const ROLE_LABELS = {
  support_manager: "Support Manager",
  customer: "Customer",
};

/**
 * Read-only account details -- reached from the profile dropdown in
 * every authenticated header (ProfileMenu). Email is shown but
 * disabled: it's the person's login identity, not something this demo
 * app lets anyone edit here.
 *
 * Topbar brand matches the authenticated headers (QuickCrave, the
 * client's own name) rather than TicketPilot, and drops the
 * "Support, powered by..." tagline those headers use -- just the logo
 * and the client name here.
 *
 * Support managers additionally get a "Reset Demo Data" action here --
 * calls resetDemoService (POST /ticketmanagement/resetDemo), which runs
 * the sp_reset_demo() stored procedure server-side. This used to only be
 * runnable by SSHing into the VM and running a mysql command by hand;
 * now it's one tap, from a phone browser included. Customers never see
 * this -- the backend route itself is manager-only too (get_current_user),
 * so this is defense in depth, not the only check.
 */
function Profile() {
  const session = useSelector((state) => state.session.user);
  const homePath = session?.role === "support_manager" ? config.routes.approvalQueue : config.routes.submitTicket;
  const [resetting, setResetting] = useState(false);

  const handleResetDemo = async () => {
    setResetting(true);
    try {
      await resetDemoService();
      message.success("Demo data reset.");
    } catch (err) {
      message.error(err?.response?.data?.detail || "Could not reset demo data.");
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.topbar}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo size={30} />
          <span className={styles.brand}>{config.clientName}</span>
        </div>
        <div className="qc-flex-spacer" />
        <ThemeToggle />
      </div>

      <div className={styles.shell}>
        <Card className={styles.card}>
          <div className={styles.avatarRow}>
            <Avatar size={64} icon={<UserOutlined />} style={{ background: "var(--qc-primary)" }} />
            <div className={styles.name}>{session?.name || "Account"}</div>
            <span className={styles.roleTag}>{ROLE_LABELS[session?.role] || session?.role}</span>
          </div>

          <div className={styles.field}>
            <span className={styles.label}>Full name</span>
            <Input value={session?.name || ""} disabled />
          </div>

          <div className={styles.field}>
            <span className={styles.label}>Email</span>
            <Input value={session?.email || ""} disabled />
          </div>

          <Typography.Paragraph type="secondary" style={{ fontSize: 12.5, marginBottom: 0 }}>
            Need to change these details? Contact your administrator -- account info isn't editable from here.
          </Typography.Paragraph>

          {session?.role === "support_manager" && (
            <>
              <Divider style={{ margin: "20px 0 16px" }} />
              <Popconfirm
                title="Reset all demo data?"
                description="This wipes every ticket, message, and approval, and re-times the two demo orders relative to right now. This can't be undone."
                okText="Reset"
                okButtonProps={{ danger: true }}
                onConfirm={handleResetDemo}
              >
                <Button danger block loading={resetting}>
                  Reset Demo Data
                </Button>
              </Popconfirm>
            </>
          )}
        </Card>

        <Typography.Paragraph style={{ marginTop: 16, textAlign: "center" }}>
          <Link to={homePath}>← Back</Link>
        </Typography.Paragraph>
      </div>
    </div>
  );
}

export default Profile;
