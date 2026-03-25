import { NavLink, Outlet } from "react-router-dom";
import Header from "../components/Header";
import styles from "./Settings.module.css";

const NAV = [
  { to: "/settings", label: "Account", end: true },
  { to: "/settings/profile", label: "Profile" },
  { to: "/settings/notifications", label: "Notifications" },
  { to: "/settings/friend-groups", label: "Friend Groups" },
  { to: "/settings/data", label: "Data & Privacy" },
];

export default function Settings() {
  return (
    <>
      <Header left={<span>Settings</span>} />
      <div className={styles.container}>
        <nav className={styles.nav} aria-label="Settings navigation">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.active : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className={styles.content}>
          <Outlet />
        </div>
      </div>
    </>
  );
}
