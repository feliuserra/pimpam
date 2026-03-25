import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import * as usersApi from "../../api/users";
import styles from "./SettingsForm.module.css";

export default function DataSettings() {
  const { user } = useAuth();
  const isDeletionScheduled = !!user?.deletion_scheduled_at;

  return (
    <div>
      <DataExportSection />
      <hr className={styles.divider} />
      <DeleteAccountSection scheduled={isDeletionScheduled} />
    </div>
  );
}

function DataExportSection() {
  const [downloading, setDownloading] = useState(false);
  const [status, setStatus] = useState(null);

  const handleExport = async () => {
    setDownloading(true);
    setStatus(null);
    try {
      const res = await usersApi.exportData();
      // Trigger file download
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pimpam-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setStatus({ type: "success", msg: "Download started." });
    } catch {
      setStatus({ type: "error", msg: "Export failed. Try again later." });
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Data Export</h3>
      <p className={styles.hint}>
        Download a copy of all your data including posts, comments, messages, and profile info.
      </p>
      {status && (
        <p className={status.type === "error" ? styles.error : styles.success} role="alert">
          {status.msg}
        </p>
      )}
      <button className={styles.btn} onClick={handleExport} disabled={downloading}>
        {downloading ? "Preparing..." : "Download my data"}
      </button>
    </section>
  );
}

function DeleteAccountSection({ scheduled }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);

  const handleDelete = async (e) => {
    e.preventDefault();
    if (!window.confirm(
      "Are you sure? Your account will be permanently deleted after 7 days. You can cancel during the grace period."
    )) return;
    setBusy(true);
    setStatus(null);
    try {
      await usersApi.deleteAccount(password);
      setStatus({ type: "success", msg: "Account scheduled for deletion in 7 days." });
      setPassword("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to delete account" });
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    setBusy(true);
    setStatus(null);
    try {
      await usersApi.cancelDeletion();
      setStatus({ type: "success", msg: "Deletion cancelled. Your account is active again." });
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to cancel deletion" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={`${styles.heading} ${styles.dangerText}`}>Delete Account</h3>

      {status && (
        <p className={status.type === "error" ? styles.error : styles.success} role="alert">
          {status.msg}
        </p>
      )}

      {scheduled ? (
        <div>
          <p className={styles.hint}>
            Your account is scheduled for deletion. During the 7-day grace period, you can cancel.
          </p>
          <button className={styles.btn} onClick={handleCancel} disabled={busy}>
            {busy ? "Cancelling..." : "Cancel deletion"}
          </button>
        </div>
      ) : (
        <div>
          <p className={styles.hint}>
            This will permanently delete your account after a 7-day grace period. Your posts and comments will be anonymized. This cannot be undone.
          </p>
          <form className={styles.form} onSubmit={handleDelete}>
            <label className={styles.label}>
              Confirm your password
              <input
                className={styles.input}
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            <button type="submit" className={`${styles.btn} ${styles.dangerBtn}`} disabled={busy || !password}>
              {busy ? "Processing..." : "Delete my account"}
            </button>
          </form>
        </div>
      )}
    </section>
  );
}
