import { Avatar, Dropdown } from "antd";
import { UserOutlined, LogoutOutlined } from "@ant-design/icons";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

import config from "../../data/config";
import { clearSession } from "../../store/sessionSlice";
import styles from "./ProfileMenu.module.css";

/**
 * Shared profile control for every authenticated header (customer
 * BrandBar, manager AppLayout) -- just the avatar icon, opening a small
 * dropdown with "View Profile" (-> /profile, read-only) and "Log out".
 * No name text and no dropdown chevron next to the icon -- the icon
 * alone is the trigger.
 */
function ProfileMenu() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const session = useSelector((state) => state.session.user);

  const handleLogout = () => {
    dispatch(clearSession());
    navigate(session?.role === "support_manager" ? config.routes.login : config.routes.landing, {
      replace: true,
    });
  };

  const items = [
    { key: "profile", icon: <UserOutlined />, label: "View Profile" },
    { type: "divider" },
    { key: "logout", icon: <LogoutOutlined />, label: "Log out", danger: true },
  ];

  const onClick = ({ key }) => {
    if (key === "profile") navigate(config.routes.profile);
    if (key === "logout") handleLogout();
  };

  if (!session) return null;

  return (
    <Dropdown menu={{ items, onClick }} trigger={["click"]} placement="bottomRight">
      <button type="button" className={styles.trigger} aria-label="Account menu">
        <Avatar size={30} icon={<UserOutlined />} className={styles.avatar} />
      </button>
    </Dropdown>
  );
}

export default ProfileMenu;
