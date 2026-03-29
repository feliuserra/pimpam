import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../contexts/ToastContext";
import * as devicesApi from "../../api/devices";
import { createBackup } from "../../crypto/backup";
import RelativeTime from "../../components/ui/RelativeTime";
import Spinner from "../../components/ui/Spinner";
import styles from "./SettingsForm.module.css";

export default function SecuritySettings() {
  return (
    <div>
      <DevicesSection />
      <hr className={styles.divider} />
      <BackupSection />
    </div>
  );
}

function DevicesSection() {
  const { deviceId } = useAuth();
  const { addToast } = useToast();
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");

  const loadDevices = useCallback(async () => {
    try {
      const { data } = await devicesApi.getMyDevices();
      setDevices(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const handleRename = async (id) => {
    if (!editName.trim()) return;
    try {
      await devicesApi.renameDevice(id, editName.trim());
      setEditingId(null);
      loadDevices();
    } catch {
      addToast("Failed to rename device", "error");
    }
  };

  const handleRevoke = async (id) => {
    if (!window.confirm("Revoke this device? New messages won't be encrypted for it.")) return;
    try {
      await devicesApi.revokeDevice(id);
      loadDevices();
      addToast("Device revoked", "success");
    } catch {
      addToast("Failed to revoke device", "error");
    }
  };

  if (loading) {
    return (
      <section className={styles.section}>
        <h3 className={styles.heading}>Your devices</h3>
        <div className={styles.loader}><Spinner size={20} /></div>
      </section>
    );
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Your devices</h3>
      {devices.length === 0 ? (
        <p className={styles.hint}>No devices registered.</p>
      ) : (
        <div className={styles.toggleList}>
          {devices.map((d) => (
            <div key={d.id} className={styles.toggleRow} style={{ flexDirection: "column", alignItems: "stretch", gap: 4, cursor: "default" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                {editingId === d.id ? (
                  <form onSubmit={(e) => { e.preventDefault(); handleRename(d.id); }} style={{ display: "flex", gap: 4, flex: 1 }}>
                    <input
                      className={styles.input}
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      maxLength={100}
                      autoFocus
                      style={{ flex: 1, padding: "4px 8px", fontSize: "0.85rem" }}
                    />
                    <button type="submit" className={styles.btn} style={{ padding: "4px 12px", fontSize: "0.8rem" }}>Save</button>
                    <button type="button" className={styles.linkBtn} onClick={() => setEditingId(null)} style={{ padding: "4px 8px" }}>Cancel</button>
                  </form>
                ) : (
                  <>
                    <span style={{ fontWeight: 500 }}>
                      {d.device_name}
                      {d.id === deviceId && <span className={styles.badge} style={{ marginLeft: 8 }}>This device</span>}
                    </span>
                    <span style={{ display: "flex", gap: 4, alignItems: "center" }}>
                      <button
                        className={styles.linkBtn}
                        onClick={() => { setEditingId(d.id); setEditName(d.device_name); }}
                        style={{ padding: "2px 6px", fontSize: "0.78rem" }}
                      >
                        Rename
                      </button>
                      {d.id !== deviceId && (
                        <button
                          className={styles.deleteSmall}
                          onClick={() => handleRevoke(d.id)}
                        >
                          Revoke
                        </button>
                      )}
                    </span>
                  </>
                )}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                <span title={d.public_key_fingerprint}>
                  {d.public_key_fingerprint.slice(0, 16)}...
                </span>
                <span>Last seen <RelativeTime date={d.last_seen_at} /></span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function BackupSection() {
  const { extractablePrivateKey, deviceId } = useAuth();
  const { addToast } = useToast();
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [passphrase, setPassphrase] = useState("");
  const [confirmPassphrase, setConfirmPassphrase] = useState("");
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const loadBackups = useCallback(async () => {
    try {
      const { data } = await devicesApi.getAvailableBackups();
      setBackups(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBackups();
  }, [loadBackups]);

  const hasBackup = backups.some((b) => b.device_id === deviceId);

  const handleCreateBackup = async (e) => {
    e.preventDefault();
    if (passphrase.length < 12) {
      addToast("Passphrase must be at least 12 characters", "error");
      return;
    }
    if (passphrase !== confirmPassphrase) {
      addToast("Passphrases don't match", "error");
      return;
    }
    if (!extractablePrivateKey) {
      addToast("Key not available for backup. Try logging out and back in.", "error");
      return;
    }
    setCreating(true);
    try {
      const backupData = await createBackup(passphrase, extractablePrivateKey);
      await devicesApi.uploadBackup(deviceId, backupData);
      addToast("Key backed up successfully", "success");
      setPassphrase("");
      setConfirmPassphrase("");
      setShowForm(false);
      loadBackups();
    } catch (err) {
      addToast("Failed to create backup", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteBackup = async () => {
    if (!window.confirm("Delete your key backup? You won't be able to recover your key on new devices.")) return;
    try {
      await devicesApi.deleteBackup(deviceId);
      addToast("Backup deleted", "success");
      loadBackups();
    } catch {
      addToast("Failed to delete backup", "error");
    }
  };

  if (loading) {
    return (
      <section className={styles.section}>
        <h3 className={styles.heading}>Key backup</h3>
        <div className={styles.loader}><Spinner size={20} /></div>
      </section>
    );
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Key backup</h3>
      <p className={styles.hint}>
        Back up your encryption key so you can recover it on new devices.
        Your key is encrypted with a passphrase before being stored.
      </p>

      {hasBackup ? (
        <div>
          <p className={styles.success}>Your key is backed up.</p>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button className={styles.btn} onClick={() => setShowForm(true)}>Update backup</button>
            <button className={`${styles.btn} ${styles.dangerBtn}`} onClick={handleDeleteBackup}>Delete backup</button>
          </div>
        </div>
      ) : (
        <div>
          <p className={styles.hint} style={{ color: "var(--color-danger, #e53e3e)" }}>
            Not backed up. If you lose this device, your messages cannot be recovered.
          </p>
          {!showForm && (
            <button className={styles.btn} onClick={() => setShowForm(true)}>Create backup</button>
          )}
        </div>
      )}

      {showForm && (
        <form className={styles.form} onSubmit={handleCreateBackup} style={{ marginTop: 16 }}>
          <label className={styles.label}>
            Passphrase (min 12 characters)
            <input
              type="password"
              className={styles.input}
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              minLength={12}
              required
              autoComplete="new-password"
            />
          </label>
          <label className={styles.label}>
            Confirm passphrase
            <input
              type="password"
              className={styles.input}
              value={confirmPassphrase}
              onChange={(e) => setConfirmPassphrase(e.target.value)}
              required
              autoComplete="new-password"
            />
          </label>
          <p className={styles.hint}>
            If you forget this passphrase and lose all devices, your messages cannot be recovered.
          </p>
          <div className={styles.row}>
            <button type="submit" className={styles.btn} disabled={creating}>
              {creating ? "Encrypting..." : "Back up key"}
            </button>
            <button type="button" className={styles.linkBtn} onClick={() => { setShowForm(false); setPassphrase(""); setConfirmPassphrase(""); }}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
