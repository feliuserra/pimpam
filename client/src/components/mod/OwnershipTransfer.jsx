import { useState } from "react";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

export default function OwnershipTransfer({ communityName }) {
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy || !username.trim()) return;
    if (!window.confirm(`Transfer ownership of c/${communityName} to @${username.trim()}?`)) return;
    setBusy(true);
    setStatus(null);
    try {
      await modApi.proposeTransfer(communityName, {
        recipient_username: username.trim(),
      });
      setStatus({ type: "success", msg: "Transfer proposed. Waiting for recipient to accept." });
      setUsername("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to propose transfer" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h3 className={styles.heading}>Ownership Transfer</h3>
      <p className={styles.hint}>
        Transfer community ownership to another senior moderator. The recipient must accept.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Recipient username"
          required
        />

        {status && (
          <p className={status.type === "error" ? styles.error : styles.success} role="alert">
            {status.msg}
          </p>
        )}

        <button type="submit" className={`${styles.dangerBtn}`} disabled={busy || !username.trim()}>
          {busy ? "Submitting..." : "Propose Transfer"}
        </button>
      </form>
    </div>
  );
}
