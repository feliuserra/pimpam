import { useState, useEffect } from "react";
import Spinner from "../ui/Spinner";
import RelativeTime from "../ui/RelativeTime";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

export default function QueueTab({ communityName }) {
  const [reports, setReports] = useState([]);
  const [removed, setRemoved] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    Promise.all([
      modApi.listReports(communityName, "pending"),
      modApi.listRemoved(communityName),
    ])
      .then(([reportsRes, removedRes]) => {
        setReports(reportsRes.data);
        setRemoved(removedRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [communityName]);

  const handleResolve = async (reportId, action) => {
    try {
      await modApi.resolveReport(communityName, reportId, action);
      fetchData();
    } catch {
      // silent
    }
  };

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;

  return (
    <div>
      {/* Reported content */}
      <h3 className={styles.heading}>Reported Content ({reports.length})</h3>
      {reports.length === 0 ? (
        <p className={styles.empty}>No pending reports.</p>
      ) : (
        <div className={styles.list}>
          {reports.map((r) => (
            <div key={r.id} className={styles.card}>
              <div className={styles.cardRow}>
                <strong>{r.content_type}: #{r.content_id}</strong>
                <span className={styles.badge}>{r.status}</span>
              </div>
              {r.content_preview && (
                <p className={styles.cardText}>{r.content_preview}</p>
              )}
              <div className={styles.cardMeta}>
                <span>Reported by @{r.reporter_username} — {r.reason}</span>
                <RelativeTime date={r.created_at} />
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button
                  className={styles.dangerBtn}
                  onClick={() => handleResolve(r.id, "remove")}
                >
                  Remove
                </button>
                <button
                  className={styles.smallBtn}
                  onClick={() => handleResolve(r.id, "dismiss")}
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Removed content */}
      <h3 className={styles.heading} style={{ marginTop: 24 }}>
        Removed Content ({removed.length})
      </h3>
      {removed.length === 0 ? (
        <p className={styles.empty}>No removed content.</p>
      ) : (
        <div className={styles.list}>
          {removed.map((item, i) => (
            <div key={`${item.type}-${item.id}-${i}`} className={styles.card}>
              <div className={styles.cardRow}>
                <strong>{item.type}: #{item.id}</strong>
              </div>
              <p className={styles.cardText}>{item.preview || "(no content)"}</p>
              <div className={styles.cardMeta}>
                <span>Removed by {item.removed_by || "unknown"}</span>
                {item.created_at && <RelativeTime date={item.created_at} />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
