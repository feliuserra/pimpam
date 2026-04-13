import { Navigate, Outlet } from "react-router-dom";
import BottomTabBar from "../components/BottomTabBar";
import Sidebar from "../components/Sidebar";
import VerificationBanner from "../components/VerificationBanner";
import { useAuth } from "../contexts/AuthContext";
import Spinner from "../components/ui/Spinner";
import styles from "./AppShell.module.css";

export default function AppShell() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className={styles.loading}>
        <Spinner size={32} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skipLink}>
        Skip to main content
      </a>
      <Sidebar />
      <main id="main-content" className={styles.main}>
        {!user.is_verified && <VerificationBanner />}
        <Outlet />
      </main>
      <BottomTabBar />
    </div>
  );
}
