import { useState } from "react";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

export default function ModPromotion({ communityName }) {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("moderator");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy || !username.trim()) return;
    setBusy(true);
    setStatus(null);
    try {
      const res = await modApi.proposeMod(communityName, {
        target_username: username.trim(),
        target_role: role,
      });
      setStatus({
        type: "success",
        msg: `Proposal created. Votes: ${res.data.vote_count}/${res.data.required_votes}`,
      });
      setUsername("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to propose" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h3 className={styles.heading}>Propose Moderator</h3>
      <p className={styles.hint}>
        Target must have 200+ community karma for moderator, 500+ for senior mod.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          required
        />
        <select className={styles.input} value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="moderator">Moderator</option>
          <option value="senior_mod">Senior Moderator</option>
        </select>

        {status && (
          <p className={status.type === "error" ? styles.error : styles.success} role="alert">
            {status.msg}
          </p>
        )}

        <button type="submit" className={styles.btn} disabled={busy || !username.trim()}>
          {busy ? "Submitting..." : "Propose"}
        </button>
      </form>
    </div>
  );
}
