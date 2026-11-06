import { useState } from "react";
import { Alert, Button, Form, Input, Typography } from "antd";
import { useDispatch } from "react-redux";
import { useNavigate, Link } from "react-router-dom";

import config from "../../data/config";
import { loginService } from "../../utils/apiHelper";
import { setSession } from "../../store/sessionSlice";
import Logo from "../../components/Logo/Logo";
import ThemeToggle from "../../components/ThemeToggle/ThemeToggle";
import SilkBackground from "../../components/SilkBackground/SilkBackground";
import styles from "./Login.module.css";

/**
 * One shared login for both principals TicketPilot knows about -- the
 * backend's /auth/login tries the User (manager) table first, then
 * Customer, by email, and returns whichever role actually matched. We
 * don't ask or assume which one the person is; we just read `role` back
 * and send them to the right home.
 *
 * Same Silk shader as the Landing page, but full-bleed behind the whole
 * page rather than split-screen, with the header and the login panel
 * floating over it on a frosted-glass layer (backdrop-filter blur) so
 * the animation stays visible through both.
 */
function Login() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const onFinish = async (values) => {
    setError(null);
    setSubmitting(true);
    try {
      const data = await loginService(values.email, values.password);
      dispatch(
        setSession({
          accessToken: data.access_token,
          userId: data.user_id,
          role: data.role,
          name: data.name,
          // Not returned by /auth/login -- the person just typed it, and
          // the Profile page shows it back as a (non-editable) detail.
          email: values.email,
        }),
      );
      navigate(
        data.role === "support_manager" ? config.routes.approvalQueue : config.routes.submitTicket,
        { replace: true },
      );
    } catch (err) {
      setError(err?.response?.data?.detail || "Invalid email or password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.page}>
      <SilkBackground className={styles.bg} />
      <div className={styles.scrim} />

      <div className={styles.topbar}>
        <Link to={config.routes.landing} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Logo size={30} />
          <span className={styles.brand}>{config.platformName}</span>
        </Link>
        <div className="qc-flex-spacer" />
        <ThemeToggle />
      </div>

      <div className={styles.center}>
        <div className={styles.panel}>
          <div className={styles.panelHeading}>
            <Typography.Title level={3} className={styles.panelTitle}>
              Welcome back
            </Typography.Title>
            <Typography.Text type="secondary">Log in to continue to {config.platformName}</Typography.Text>
          </div>

          {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}

          <Form layout="vertical" onFinish={onFinish} className={styles.form} requiredMark={false}>
            <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}>
              <Input size="large" autoFocus placeholder="you@example.com" />
            </Form.Item>
            <Form.Item name="password" label="Password" rules={[{ required: true }]}>
              <Input.Password size="large" placeholder="••••••••" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} block className={styles.submit}>
              Log in
            </Button>
          </Form>

          <div className={styles.demoHints}>
            <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 2 }}>
              Demo customer: rohan.deshmukh@example.com / Customer@123
            </Typography.Paragraph>
            <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 2 }}>
              Demo customer: ananya.iyer@example.com / Customer@123
            </Typography.Paragraph>
            <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
              Demo manager: harshal.pawar@quickcrave.com / Manager@123
            </Typography.Paragraph>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
