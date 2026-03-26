import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Header from "../components/Header";
import Spinner from "../components/ui/Spinner";
import { useAuth } from "../contexts/AuthContext";
import * as adminApi from "../api/admin";
import styles from "./AdminDashboard.module.css";

const PERIODS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

export default function AdminDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [signups, setSignups] = useState([]);
  const [posts, setPosts] = useState([]);
  const [topCommunities, setTopCommunities] = useState([]);
  const [moderation, setModeration] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user && !user.is_admin) {
      navigate("/", { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    if (!user?.is_admin) return;
    setLoading(true);
    Promise.all([
      adminApi.getOverview(),
      adminApi.getTimeseries("signups", days),
      adminApi.getTimeseries("posts", days),
      adminApi.getTopCommunities(days),
      adminApi.getModerationSummary(days),
    ])
      .then(([ov, sig, pos, top, mod]) => {
        setOverview(ov.data);
        setSignups(sig.data);
        setPosts(pos.data);
        setTopCommunities(top.data);
        setModeration(mod.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, days]);

  if (!user?.is_admin) return null;

  return (
    <>
      <Header
        left={<span className={styles.headerTitle}>Dashboard</span>}
        right={
          <div className={styles.periodSelector}>
            {PERIODS.map((p) => (
              <button
                key={p.days}
                className={`${styles.periodBtn} ${days === p.days ? styles.periodActive : ""}`}
                onClick={() => setDays(p.days)}
              >
                {p.label}
              </button>
            ))}
          </div>
        }
      />

      <div className={styles.container}>
        {loading ? (
          <div className={styles.loader}><Spinner size={28} /></div>
        ) : (
          <>
            {/* Overview cards */}
            {overview && (
              <div className={styles.cards}>
                <StatCard label="Users" value={overview.total_users} />
                <StatCard label="Posts" value={overview.total_posts} />
                <StatCard label="Comments" value={overview.total_comments} />
                <StatCard label="Active (7d)" value={overview.active_users_7d} />
              </div>
            )}

            {/* Signups chart */}
            <section className={styles.chartSection}>
              <h3 className={styles.chartTitle}>Signups</h3>
              <ChartArea data={signups} color="#6366f1" />
            </section>

            {/* Posts chart */}
            <section className={styles.chartSection}>
              <h3 className={styles.chartTitle}>Posts</h3>
              <ChartArea data={posts} color="#10b981" />
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
                      <span className={styles.statMuted}>{c.member_count.toLocaleString()} members</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Moderation */}
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

function StatCard({ label, value }) {
  return (
    <div className={styles.statCard}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue}>{value.toLocaleString()}</span>
    </div>
  );
}

function ChartArea({ data, color }) {
  if (!data || data.length === 0) {
    return <p className={styles.empty}>No data for this period.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "var(--color-text-muted)" }}
          tickFormatter={(d) => d.slice(5)}
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
        />
        <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
