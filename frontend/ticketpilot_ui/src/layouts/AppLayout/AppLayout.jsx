import { Outlet } from "react-router-dom";
import { Layout, Typography } from "antd";

import config from "../../data/config";
import Logo from "../../components/Logo/Logo";
import ThemeToggle from "../../components/ThemeToggle/ThemeToggle";
import ProfileMenu from "../../components/ProfileMenu/ProfileMenu";
import styles from "./AppLayout.module.css";

const { Header, Content } = Layout;

/**
 * Shell for the authenticated support-manager area. A simple top bar --
 * no sidebar needed since the manager dashboard is a single page
 * (pending approvals + escalated tickets) rather than several. Account
 * info + logout live in the shared ProfileMenu dropdown now, same
 * pattern as the customer-facing BrandBar.
 */
function AppLayout() {
  return (
    <Layout style={{ minHeight: "100vh", background: "var(--qc-bg)" }}>
      <Header className={styles.header}>
        <div className={styles.brandGroup}>
          <Logo />
          <Typography.Title level={4} className={styles.title}>
            {`${config.platformName} — Support Manager`}
          </Typography.Title>
        </div>
        <div className={styles.actions}>
          <ThemeToggle />
          <ProfileMenu />
        </div>
      </Header>
      <Content style={{ padding: "24px" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}

export default AppLayout;
