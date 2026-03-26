import { useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api/auth";
import styles from "./Auth.module.css";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await requestPasswordReset(email);
    } catch {
      // Always show success to prevent email enumeration
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>

      {submitted ? (
        <>
          <h2 style={{ fontSize: "1.125rem", marginTop: "0.5rem" }}>Check your email</h2>
          <p style={{ color: "var(--text-secondary)", marginTop: "0.5rem", lineHeight: 1.6 }}>
            If an account exists with that email, we sent a password reset link.
            It expires in 15 minutes.
          </p>
          <p className={styles.footer}>
            <Link to="/login">Back to sign in</Link>
          </p>
        </>
      ) : (
        <>
          <p style={{ color: "var(--text-secondary)", marginBottom: "1.5rem", fontSize: "0.9375rem" }}>
            Enter your email and we'll send a reset link.
          </p>

          <form className={styles.form} onSubmit={handleSubmit}>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <button type="submit" disabled={loading}>
              {loading ? "Sending\u2026" : "Send reset link"}
            </button>
          </form>

          <p className={styles.footer}>
            <Link to="/login">Back to sign in</Link>
          </p>
        </>
      )}
    </main>
  );
}
