import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/client";
import styles from "./Auth.module.css";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/register", form);
      // Auto-login after registration
      const { data } = await api.post("/auth/login", {
        username: form.username,
        password: form.password,
      });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>
      <p className={styles.tagline}>Join the open social network.</p>

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

        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className={styles.footer}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  );
}
