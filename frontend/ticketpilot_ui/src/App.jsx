import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { message } from "antd";

import Landing from "./pages/Landing/Landing";
import SubmitTicket from "./pages/SubmitTicket/SubmitTicket";
import MyTickets from "./pages/MyTickets/MyTickets";
import TicketDetail from "./pages/TicketDetail/TicketDetail";
import Login from "./pages/Login/Login";
import Profile from "./pages/Profile/Profile";
import ApprovalQueue from "./pages/ApprovalQueue/ApprovalQueue";
import AppLayout from "./layouts/AppLayout/AppLayout";
import config from "./data/config";
import { loadSession, clearSession } from "./store/sessionSlice";
import { AUTH_EXPIRED_EVENT } from "./utils/apiHelper";

// Where a logged-in session's own home is, by role -- used by both
// guards below and the catch-all route.
function homeFor(session) {
  if (!session) return config.routes.landing;
  return session.role === "support_manager" ? config.routes.approvalQueue : config.routes.submitTicket;
}

// Guards Landing and /login -- bounces any logged-in session straight
// to their own home instead of showing either page.
function RequireGuest({ children }) {
  const session = useSelector((state) => state.session.user);
  const loaded = useSelector((state) => state.session.loaded);

  if (!loaded) return null;
  if (session) return <Navigate to={homeFor(session)} replace />;

  return children;
}

// Redirects to /login when there's no active support-manager session --
// guards the authenticated manager area (ApprovalQueue). A logged-in
// CUSTOMER hitting this is also not a manager, so they're sent to their
// own home rather than let through.
function RequireAuth({ children }) {
  const session = useSelector((state) => state.session.user);
  const loaded = useSelector((state) => state.session.loaded);

  if (!loaded) return null;
  if (!session) return <Navigate to={config.routes.login} replace />;
  if (session.role !== "support_manager") return <Navigate to={homeFor(session)} replace />;

  return children;
}

// The customer-only counterpart: a logged-in support manager should
// never land on the customer self-service pages -- that's not their
// job. Someone with no session at all is sent to log in rather than
// straight to a customer page, since customer identity now comes
// exclusively from the JWT (there's no more "type your customer ID").
// TicketDetail is deliberately NOT behind this guard -- a manager needs
// to open a ticket's conversation for context (from ApprovalCard /
// EscalatedTicketCard), it just renders a different, read-only view for
// them (see TicketDetail.jsx).
function RequireCustomerAuth({ children }) {
  const session = useSelector((state) => state.session.user);
  const loaded = useSelector((state) => state.session.loaded);

  if (!loaded) return null;
  if (!session) return <Navigate to={config.routes.login} replace />;
  if (session.role !== "customer") return <Navigate to={homeFor(session)} replace />;

  return children;
}

// Role-agnostic guard -- just "is someone logged in at all". Used by
// /profile, which both a customer and a support manager can reach from
// their own header's ProfileMenu dropdown.
function RequireAnyAuth({ children }) {
  const session = useSelector((state) => state.session.user);
  const loaded = useSelector((state) => state.session.loaded);

  if (!loaded) return null;
  if (!session) return <Navigate to={config.routes.login} replace />;

  return children;
}

function App() {
  const dispatch = useDispatch();
  const session = useSelector((state) => state.session.user);
  const sessionLoaded = useSelector((state) => state.session.loaded);

  // Rehydrate the session from localStorage once on app load.
  useEffect(() => {
    dispatch(loadSession());
  }, [dispatch]);

  const endExpiredSession = () => {
    dispatch(clearSession());
    message.warning("Your session has expired. Please log in again.");
  };

  // apiHelper.js's response interceptor fires this window event on
  // every 401 -- this is where it's actually handled.
  useEffect(() => {
    const handleAuthExpired = () => endExpiredSession();
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  // Proactive expiry -- schedules a real timer for exactly when the
  // current session's expiresAt arrives, instead of waiting for some
  // unrelated event to trigger a re-check.
  useEffect(() => {
    if (!session?.expiresAt) return undefined;

    const msRemaining = session.expiresAt - Date.now();
    if (msRemaining <= 0) {
      endExpiredSession();
      return undefined;
    }

    const timer = setTimeout(endExpiredSession, msRemaining);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.expiresAt]);

  return (
    <Routes>
      {/* Public -- no login required, and off-limits to ANY logged-in
          session (bounced to their own home instead). */}
      <Route
        path={config.routes.landing}
        element={
          <RequireGuest>
            <Landing />
          </RequireGuest>
        }
      />

      <Route
        path={config.routes.login}
        element={
          <RequireGuest>
            <Login />
          </RequireGuest>
        }
      />

      {/* Customer-only -- requires a logged-in customer JWT; a manager
          is redirected to their own dashboard, a guest to /login. */}
      <Route
        path={config.routes.submitTicket}
        element={
          <RequireCustomerAuth>
            <SubmitTicket />
          </RequireCustomerAuth>
        }
      />
      <Route
        path={config.routes.myTickets}
        element={
          <RequireCustomerAuth>
            <MyTickets />
          </RequireCustomerAuth>
        }
      />

      {/* Shared between customer and manager -- requires SOME login
          (the backend 401s otherwise), and renders a different,
          read-only view for a logged-in manager (see TicketDetail.jsx). */}
      <Route path={config.routes.ticketDetail} element={<TicketDetail />} />

      {/* Shared account-details page, reached from either header's
          ProfileMenu dropdown -- any logged-in role may open it. */}
      <Route
        path={config.routes.profile}
        element={
          <RequireAnyAuth>
            <Profile />
          </RequireAnyAuth>
        }
      />

      {/* Authenticated support-manager area */}
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path={config.routes.approvalQueue} element={<ApprovalQueue />} />
      </Route>

      <Route
        path="*"
        element={!sessionLoaded ? null : <Navigate to={homeFor(session)} replace />}
      />
    </Routes>
  );
}

export default App;
