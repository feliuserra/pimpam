import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import styles from "./Auth.module.css";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/auth/login", form);
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Login failed");
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
          required
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className={styles.footer}>
        No account? <Link to="/register">Create one</Link>
      </p>
    </main>
  );
}
