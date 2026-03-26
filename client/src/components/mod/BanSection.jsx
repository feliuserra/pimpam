import { useState, useEffect } from "react";
import Spinner from "../ui/Spinner";
import RelativeTime from "../ui/RelativeTime";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

const COC_VIOLATIONS = [
  "HARASSMENT",
  "HATE_SPEECH",
  "ABUSE",
  "SPAM",
  "IMPERSONATION",
  "NSFW",
  "OTHER",
];

export default function BanSection({ communityName }) {
  const [bans, setBans] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showPropose, setShowPropose] = useState(false);

  useEffect(() => {
    Promise.all([
      modApi.listBans(communityName),
      modApi.listAppeals(communityName),
    ])
      .then(([bansRes, appealsRes]) => {
        setBans(bansRes.data);
        setAppeals(appealsRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [communityName]);

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;

  return (
    <div>
      <div className={styles.sectionHeader}>
        <h3 className={styles.heading}>Ban Proposals</h3>
        <button className={styles.btn} onClick={() => setShowPropose(!showPropose)}>
          {showPropose ? "Cancel" : "Propose Ban"}
        </button>
      </div>

      {showPropose && (
        <ProposeBanForm
          communityName={communityName}
          onCreated={() => {
            setShowPropose(false);
            modApi.listBans(communityName).then((r) => setBans(r.data)).catch(() => {});
          }}
        />
      )}

      {/* Active bans */}
      <h4 className={styles.subheading}>Active Bans ({bans.length})</h4>
      {bans.length === 0 ? (
        <p className={styles.empty}>No active bans.</p>
      ) : (
        <div className={styles.list}>
          {bans.map((ban) => (
            <div key={ban.id} className={styles.card}>
              <div className={styles.cardRow}>
                <strong>User #{ban.user_id}</strong>
                <span className={styles.badge}>{ban.is_permanent ? "Permanent" : "Temporary"}</span>
              </div>
              <p className={styles.cardText}>{ban.reason}</p>
              <div className={styles.cardMeta}>
                <span>Violation: {ban.coc_violation}</span>
                <RelativeTime date={ban.created_at} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Appeals */}
      <h4 className={styles.subheading}>Pending Appeals ({appeals.length})</h4>
      {appeals.length === 0 ? (
        <p className={styles.empty}>No pending appeals.</p>
      ) : (
        <div className={styles.list}>
          {appeals.map((appeal) => (
            <div key={appeal.id} className={styles.card}>
              <p className={styles.cardText}>{appeal.reason}</p>
              <div className={styles.cardMeta}>
                <span>Votes: {appeal.vote_count}/{appeal.required_votes}</span>
                <RelativeTime date={appeal.created_at} />
              </div>
              <button
                className={styles.smallBtn}
                onClick={() => {
                  modApi.voteAppeal(communityName, appeal.id)
                    .then(() => modApi.listAppeals(communityName).then((r) => setAppeals(r.data)))
                    .catch(() => {});
                }}
              >
                Vote to Accept
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProposeBanForm({ communityName, onCreated }) {
  const [username, setUsername] = useState("");
  const [reason, setReason] = useState("");
  const [violation, setViolation] = useState("other");
  const [permanent, setPermanent] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await modApi.proposeBan(communityName, {
        target_username: username.trim(),
        reason: reason.trim(),
        coc_violation: violation,
        is_permanent: permanent,
      });
      onCreated();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to propose ban");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        className={styles.input}
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username to ban"
        required
      />
      <textarea
        className={styles.textarea}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for ban"
        rows={2}
        required
      />
      <select className={styles.input} value={violation} onChange={(e) => setViolation(e.target.value)}>
        {COC_VIOLATIONS.map((v) => (
          <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
        ))}
      </select>
      <label className={styles.checkLabel}>
        <input type="checkbox" checked={permanent} onChange={(e) => setPermanent(e.target.checked)} />
        Permanent ban
      </label>
      {error && <p className={styles.error} role="alert">{error}</p>}
      <button type="submit" className={styles.dangerBtn} disabled={busy}>
        {busy ? "Submitting..." : "Propose Ban"}
      </button>
    </form>
  );
}
