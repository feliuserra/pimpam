import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Header from "../components/Header";
import RelativeTime from "../components/ui/RelativeTime";
import Spinner from "../components/ui/Spinner";
import { useAuth } from "../contexts/AuthContext";
import * as adminApi from "../api/admin";
import styles from "./AdminDashboard.module.css";

const WINDOWS = [
  { label: "1h", value: "1h" },
  { label: "24h", value: "24h" },
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
];

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [window, setWindow] = useState("24h");

  // General analytics state (refreshes every 5 minutes)
  const [overview, setOverview] = useState(null);
  const [windowOverview, setWindowOverview] = useState(null);
  const [signups, setSignups] = useState([]);
  const [posts, setPosts] = useState([]);
  const [topCommunities, setTopCommunities] = useState([]);
  const [moderation, setModeration] = useState(null);
  const [loading, setLoading] = useState(true);

  // Security state (refreshes every 30 seconds)
  const [securityMetrics, setSecurityMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [securityUpdatedAt, setSecurityUpdatedAt] = useState(null);

  useEffect(() => {
    if (user && !user.is_admin) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  // General analytics — refresh every 5 minutes
  useEffect(() => {
    if (!user?.is_admin) return;

    const fetchGeneral = () => {
      setLoading(true);
      Promise.all([
        adminApi.getOverview(),
        adminApi.getWindowOverview(window),
        adminApi.getGranularTimeseries("signups", window),
        adminApi.getGranularTimeseries("posts", window),
        adminApi.getTopCommunities(window === "1h" ? 1 : window === "24h" ? 1 : window === "7d" ? 7 : 30),
        adminApi.getModerationSummary(window === "1h" ? 1 : window === "24h" ? 1 : window === "7d" ? 7 : 30),
      ])
        .then(([ov, wov, sig, pos, top, mod]) => {
          setOverview(ov.data);
          setWindowOverview(wov.data);
          setSignups(sig.data);
          setPosts(pos.data);
          setTopCommunities(top.data);
          setModeration(mod.data);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    };

    fetchGeneral();
    const id = setInterval(fetchGeneral, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [user, window]);

  // Security data — refresh every 30 seconds
  useEffect(() => {
    if (!user?.is_admin) return;

    const fetchSecurity = () => {
      Promise.all([
        adminApi.getSecurityMetrics(window),
        adminApi.getSecurityAlerts(),
      ])
        .then(([metrics, alertsRes]) => {
          setSecurityMetrics(metrics.data);
          setAlerts(alertsRes.data?.alerts ?? []);
          setSecurityUpdatedAt(new Date());
        })
        .catch(() => {});
    };

    fetchSecurity();
    const id = setInterval(fetchSecurity, 30 * 1000);
    return () => clearInterval(id);
  }, [user, window]);

  if (!user?.is_admin) return null;

  return (
    <>
      <Header
        left={<span className={styles.headerTitle}>Dashboard</span>}
        right={
          <div className={styles.windowSelector}>
            {WINDOWS.map((w) => (
              <button
                key={w.value}
                className={`${styles.windowBtn} ${window === w.value ? styles.windowActive : ""}`}
                onClick={() => setWindow(w.value)}
                aria-pressed={window === w.value}
              >
                {w.label}
              </button>
            ))}
          </div>
        }
      />

      <div className={styles.container}>
        {/* Section 1: Security alert banner — only shown when alerts exist */}
        <SecurityAlertBanner alerts={alerts} />

        {loading ? (
          <div className={styles.loader}>
            <Spinner size={28} />
          </div>
        ) : (
          <>
            {/* Section 2: Network health overview */}
            {windowOverview && (
              <section aria-label="Network health">
                <h3 className={styles.sectionTitle}>Network ({window})</h3>
                <div className={styles.cards}>
                  <StatCard label="Active Users" value={windowOverview.active_users} />
                  <StatCard label="New Users" value={windowOverview.new_users} />
                  <StatCard label="New Posts" value={windowOverview.new_posts} />
                  <StatCard label="Messages" value={windowOverview.new_messages} />
                </div>
              </section>
            )}

            {/* All-time totals */}
            {overview && (
              <div className={`${styles.cards} ${styles.totalsCards}`}>
                <StatCard label="Total Users" value={overview.total_users} muted />
                <StatCard label="Total Posts" value={overview.total_posts} muted />
                <StatCard label="Total Comments" value={overview.total_comments} muted />
                <StatCard label="Communities" value={overview.total_communities} muted />
              </div>
            )}

            {/* Section 3: Security metrics */}
            <SecurityMetricsPanel
              metrics={securityMetrics}
              updatedAt={securityUpdatedAt}
            />

            {/* Section 4: Charts */}
            <section className={styles.chartSection}>
              <h3 className={styles.chartTitle}>Signups</h3>
              <GranularChart data={signups} color="#6366f1" window={window} />
            </section>

            <section className={styles.chartSection}>
              <h3 className={styles.chartTitle}>Posts</h3>
              <GranularChart data={posts} color="#10b981" window={window} />
            </section>

            {/* Top communities */}
            <section className={styles.chartSection}>
              <h3 className={styles.chartTitle}>Top Communities</h3>
              {topCommunities.length === 0 ? (
                <p className={styles.empty}>No community activity in this period.</p>
              ) : (
                <div className={styles.table}>
                  {topCommunities.map((c) => (
                    <div key={c.name} className={styles.tableRow}>
                      <span className={styles.communityName}>c/{c.name}</span>
                      <span className={styles.stat}>{c.post_count} posts</span>
                      <span className={styles.statMuted}>
                        {c.member_count.toLocaleString()} members
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Moderation bar */}
            {moderation && (
              <section className={styles.modBar}>
                <span>{moderation.pending_reports} pending reports</span>
                <span className={styles.modDot}>&middot;</span>
                <span>{moderation.bans_count} bans</span>
                <span className={styles.modDot}>&middot;</span>
                <span>{moderation.removals_count} removals</span>
                <span className={styles.modDot}>&middot;</span>
                <span>{moderation.suspensions_count} suspensions</span>
              </section>
            )}
          </>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Security alert banner
// ---------------------------------------------------------------------------

function SecurityAlertBanner({ alerts }) {
  if (!alerts || alerts.length === 0) return null;

  const alertClass = (type) => {
    if (type === "login_failure_ratio") return styles.alertAmber;
    return styles.alertRed;
  };

  return (
    <div className={styles.alertBanner} role="alert" aria-live="polite">
      {alerts.map((a) => (
        <div key={a.alert_type} className={`${styles.alertPill} ${alertClass(a.alert_type)}`}>
          <strong>Security alert:</strong> {a.message}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Security metrics panel
// ---------------------------------------------------------------------------

function SecurityMetricsPanel({ metrics, updatedAt }) {
  if (!metrics) return null;

  const successRate =
    metrics.successful_logins + metrics.failed_logins > 0
      ? ((1 - metrics.failure_rate) * 100).toFixed(1)
      : "N/A";

  return (
    <section className={styles.securitySection} aria-label="Security metrics">
      <h3 className={styles.sectionTitle}>
        Security
        {updatedAt && (
          <span className={styles.lastUpdated}>
            &nbsp;· Updated <RelativeTime date={updatedAt.toISOString()} />
          </span>
        )}
      </h3>

      <div className={styles.cards}>
        <StatCard label="Failed Logins" value={metrics.failed_logins} />
        <StatCard label="Success Rate" value={`${successRate}%`} raw />
        <StatCard label="Password Resets" value={metrics.password_reset_requests} />
        <StatCard label="New Registrations" value={metrics.new_registrations} />
      </div>

      {metrics.suspicious_ips && metrics.suspicious_ips.length > 0 && (
        <div className={styles.suspiciousIps}>
          <h4 className={styles.subTitle}>Suspicious IPs (by failure count)</h4>
          <p className={styles.privacyNote}>
            IP addresses are never stored in plaintext — only SHA-256 hashes are shown.
          </p>
          <div className={styles.table}>
            {metrics.suspicious_ips.map((e) => (
              <div key={e.ip_hash} className={styles.tableRow}>
                <code className={styles.ipHash}>{e.ip_hash.slice(0, 16)}&hellip;</code>
                <span className={styles.stat}>{e.failure_count} failures</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

function StatCard({ label, value, muted = false, raw = false }) {
  const displayValue = raw ? value : typeof value === "number" ? value.toLocaleString() : value;
  return (
    <div className={`${styles.statCard} ${muted ? styles.statCardMuted : ""}`}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{displayValue}</span>
    </div>
  );
}

function GranularChart({ data, color, window }) {
  if (!data || data.length === 0) {
    return <p className={styles.empty}>No data for this period.</p>;
  }

  // Format the X-axis tick based on the window granularity
  const tickFormatter = (bucket) => {
    if (window === "1h") return bucket.slice(11, 16); // HH:MM
    if (window === "24h") return bucket.slice(11, 16); // HH:00
    return bucket.slice(5); // MM-DD
  };

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="bucket"
          tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
          tickFormatter={tickFormatter}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius)",
            fontSize: "0.82rem",
          }}
          labelFormatter={tickFormatter}
        />
        <Line
          type="monotone"
          dataKey="count"
          stroke={color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
