import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import styles from "./Auth.module.css";

export default function LoginTotp() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const { username, password } = location.state || {};

  if (!username || !password) {
    return <Navigate to="/login" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password, code);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>
      <h2 style={{ fontSize: "1.125rem", marginBottom: "0.5rem" }}>
        Two-factor authentication
      </h2>
      <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Enter the 6-digit code from your authenticator app.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="totp-code">Verification code</label>
        <input
          id="totp-code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="[0-9]{6}"
          maxLength={6}
          required
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
          style={{ textAlign: "center", fontSize: "1.5rem", letterSpacing: "0.5em" }}
        />

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading || code.length !== 6}>
          {loading ? "Verifying\u2026" : "Verify"}
        </button>
      </form>

      <p className={styles.footer}>
        <button
          type="button"
          onClick={() => navigate("/login")}
          style={{ background: "none", border: "none", color: "var(--accent)", cursor: "pointer", fontFamily: "var(--font)" }}
        >
          Back to sign in
        </button>
      </p>
    </main>
  );
}
