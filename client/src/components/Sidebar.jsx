import { NavLink, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useNotifications } from "../contexts/NotificationContext";
import BellIcon from "./ui/icons/BellIcon";
import CommunityIcon from "./ui/icons/CommunityIcon";
import FriendsIcon from "./ui/icons/FriendsIcon";
import HomeIcon from "./ui/icons/HomeIcon";
import TrendingIcon from "./ui/icons/TrendingIcon";
import MessageIcon from "./ui/icons/MessageIcon";
import UserIcon from "./ui/icons/UserIcon";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  const { user } = useAuth();
  const { unreadNotifications, unreadMessages } = useNotifications();

  const links = [
    { to: "/", icon: <HomeIcon size={20} />, label: "Feed" },
    { to: "/friends", icon: <FriendsIcon size={20} />, label: "Friends" },
    { to: "/communities", icon: <CommunityIcon size={20} />, label: "Communities" },
    { to: "/discover", icon: <TrendingIcon size={20} />, label: "Discover" },
    { to: "/messages", icon: <MessageIcon size={20} />, label: "Messages", badge: unreadMessages },
    { to: "/notifications", icon: <BellIcon size={20} />, label: "Notifications", badge: unreadNotifications },
    { to: `/u/${user?.username || ""}`, icon: <UserIcon size={20} />, label: "Profile" },
  ];

  return (
    <aside className={styles.sidebar} aria-label="Main navigation">
      <Link to="/" className={styles.logo}>PimPam</Link>
      <nav className={styles.nav}>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `${styles.link} ${isActive ? styles.active : ""}`
            }
          >
            {link.icon}
            <span>{link.label}</span>
            {link.badge > 0 && (
              <span className={styles.badge} aria-label={`${link.badge} unread`}>
                {link.badge > 99 ? "99+" : link.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
