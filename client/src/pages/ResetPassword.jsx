import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { confirmPasswordReset } from "../api/auth";
import styles from "./Auth.module.css";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <main className={styles.container}>
        <h1 className={styles.logo}>PimPam</h1>
        <p className={styles.error} role="alert" style={{ marginTop: "1.5rem" }}>
          Missing reset token. Please request a new password reset link.
        </p>
        <p className={styles.footer}>
          <Link to="/forgot-password">Request reset</Link>
        </p>
      </main>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await confirmPasswordReset(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Reset failed. The link may have expired.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <main className={styles.container}>
        <h1 className={styles.logo}>PimPam</h1>
        <h2 style={{ fontSize: "1.125rem", marginTop: "0.5rem", color: "#16a34a" }}>
          Password updated
        </h2>
        <p style={{ color: "var(--text-secondary)", marginTop: "0.5rem" }}>
          You can now sign in with your new password.
        </p>
        <p className={styles.footer}>
          <Link to="/login">Sign in</Link>
        </p>
      </main>
    );
  }

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem", fontSize: "0.9375rem" }}>
        Choose a new password.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="new-password">New password</label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <label htmlFor="confirm-password">Confirm password</label>
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Updating\u2026" : "Set new password"}
        </button>
      </form>

      <p className={styles.footer}>
        <Link to="/login">Back to sign in</Link>
      </p>
    </main>
  );
}
