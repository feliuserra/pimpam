import { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../hooks/useTheme";
import * as authApi from "../../api/auth";
import styles from "./SettingsForm.module.css";

export default function AccountSettings() {
  const { user } = useAuth();

  return (
    <div>
      <ThemeToggle />
      <hr className={styles.divider} />
      <ChangePasswordForm />
      <hr className={styles.divider} />
      <TwoFactorSection enabled={user?.totp_enabled} />
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Appearance</h3>
      <label className={styles.toggleRow}>
        <span>Dark mode</span>
        <input
          type="checkbox"
          className={styles.toggle}
          checked={theme === "dark"}
          onChange={toggle}
        />
      </label>
    </section>
  );
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [status, setStatus] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setStatus(null);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setStatus({ type: "success", msg: "Password updated. Please log in again." });
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to change password" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Change Password</h3>
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label}>
          Current password
          <input
            className={styles.input}
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label className={styles.label}>
          New password
          <input
            className={styles.input}
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
          />
          <span className={styles.hint}>Min 8 characters, with uppercase, lowercase, and number</span>
        </label>
        {status && (
          <p className={status.type === "error" ? styles.error : styles.success} role="alert">
            {status.msg}
          </p>
        )}
        <button type="submit" className={styles.btn} disabled={saving}>
          {saving ? "Saving..." : "Update password"}
        </button>
      </form>
    </section>
  );
}

function TwoFactorSection({ enabled }) {
  const [step, setStep] = useState(null); // null | "setup" | "verify"
  const [uri, setUri] = useState("");
  const [secret, setSecret] = useState("");
  const [code, setCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);

  const handleSetup = async () => {
    setBusy(true);
    setStatus(null);
    try {
      const res = await authApi.totpSetup();
      setUri(res.data.uri);
      setSecret(res.data.secret);
      setStep("verify");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Setup failed" });
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await authApi.totpVerify(code);
      setStatus({ type: "success", msg: "2FA enabled!" });
      setStep(null);
      setCode("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Invalid code" });
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await authApi.totpDisable(disablePassword, disableCode);
      setStatus({ type: "success", msg: "2FA disabled." });
      setDisablePassword("");
      setDisableCode("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to disable 2FA" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Two-Factor Authentication</h3>

      {status && (
        <p className={status.type === "error" ? styles.error : styles.success} role="alert">
          {status.msg}
        </p>
      )}

      {enabled && !step ? (
        <div>
          <p className={styles.hint}>2FA is currently enabled.</p>
          <form className={styles.form} onSubmit={handleDisable}>
            <label className={styles.label}>
              Password
              <input
                className={styles.input}
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                required
              />
            </label>
            <label className={styles.label}>
              Current 2FA code
              <input
                className={styles.input}
                type="text"
                inputMode="numeric"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
                maxLength={6}
                required
                autoComplete="one-time-code"
              />
            </label>
            <button type="submit" className={`${styles.btn} ${styles.dangerBtn}`} disabled={busy}>
              {busy ? "Disabling..." : "Disable 2FA"}
            </button>
          </form>
        </div>
      ) : step === "verify" ? (
        <div>
          <p className={styles.hint}>
            Scan the QR code with your authenticator app, or enter the secret manually:
          </p>
          <div className={styles.qrContainer}>
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(uri)}`}
              alt="TOTP QR Code"
              width={200}
              height={200}
              className={styles.qr}
            />
          </div>
          <p className={styles.secret}>
            <code>{secret}</code>
          </p>
          <form className={styles.form} onSubmit={handleVerify}>
            <label className={styles.label}>
              Enter 6-digit code from app
              <input
                className={styles.input}
                type="text"
                inputMode="numeric"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                maxLength={6}
                required
                autoComplete="one-time-code"
                autoFocus
              />
            </label>
            <div className={styles.row}>
              <button type="submit" className={styles.btn} disabled={busy}>
                {busy ? "Verifying..." : "Verify & Enable"}
              </button>
              <button type="button" className={styles.linkBtn} onClick={() => setStep(null)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div>
          <p className={styles.hint}>Add an extra layer of security to your account.</p>
          <button className={styles.btn} onClick={handleSetup} disabled={busy}>
            {busy ? "Setting up..." : "Set up 2FA"}
          </button>
        </div>
      )}
    </section>
  );
}
