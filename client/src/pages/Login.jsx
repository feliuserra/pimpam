import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import styles from "./Auth.module.css";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(form.username, form.password);
      navigate("/");
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail === "totp_required") {
        navigate("/login/totp", { state: { username: form.username, password: form.password } });
        return;
      }
      const msg = typeof detail === "string"
        ? detail
        : err.message || "Login failed";
      console.error("Login error:", err.message, err.response?.status, detail);
      setError(`${msg} (${err.response?.status || "network error"})`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>
      <p className={styles.tagline}>No ads. No algorithms. No owners.</p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label htmlFor="username">Username</label>
        <input
          id="username"
          type="text"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck="false"
          required
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          autoCapitalize="none"
          required
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Signing in\u2026" : "Sign in"}
        </button>
      </form>

      <p className={styles.footer}>
        <Link to="/forgot-password">Forgot password?</Link>
      </p>
      <p className={styles.footer}>
        No account? <Link to="/register">Create one</Link>
      </p>
    </main>
  );
}
