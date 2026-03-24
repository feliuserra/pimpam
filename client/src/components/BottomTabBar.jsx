import { NavLink } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useNotifications } from "../contexts/NotificationContext";
import BellIcon from "./ui/icons/BellIcon";
import CommunityIcon from "./ui/icons/CommunityIcon";
import HomeIcon from "./ui/icons/HomeIcon";
import MessageIcon from "./ui/icons/MessageIcon";
import UserIcon from "./ui/icons/UserIcon";
import styles from "./BottomTabBar.module.css";

export default function BottomTabBar() {
  const { user } = useAuth();
  const { unreadNotifications, unreadMessages } = useNotifications();

  const tabs = [
    { to: "/", icon: <HomeIcon size={22} />, label: "Feed" },
    { to: "/communities", icon: <CommunityIcon size={22} />, label: "Communities" },
    { to: "/messages", icon: <MessageIcon size={22} />, label: "Messages", badge: unreadMessages },
    { to: "/notifications", icon: <BellIcon size={22} />, label: "Notifications", badge: unreadNotifications },
    { to: `/@${user?.username || ""}`, icon: <UserIcon size={22} />, label: "Profile" },
  ];

  return (
    <nav className={styles.bar} aria-label="Main navigation">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === "/"}
          className={({ isActive }) =>
            `${styles.tab} ${isActive ? styles.active : ""}`
          }
          aria-label={tab.label}
        >
          <span className={styles.iconWrap}>
            {tab.icon}
            {tab.badge > 0 && (
              <span className={styles.badge} aria-label={`${tab.badge} unread`}>
                {tab.badge > 99 ? "99+" : tab.badge}
              </span>
            )}
          </span>
          <span className={styles.label}>{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
