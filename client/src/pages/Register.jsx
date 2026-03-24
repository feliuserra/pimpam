import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/auth";
import { useAuth } from "../contexts/AuthContext";
import styles from "./Auth.module.css";
import regStyles from "./Register.module.css";

export default function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [consent, setConsent] = useState({ tos: false, privacy: false, age: false });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const allConsented = consent.tos && consent.privacy && consent.age;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!allConsented) {
      setError("You must accept all required agreements to create an account.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await register(form);
      await login(form.username, form.password);
      navigate("/verify-email-sent");
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((e) => e.msg || e).join(". "));
      } else {
        setError(err.message || "Registration failed");
      }
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

        <fieldset className={regStyles.consent}>
          <legend className={regStyles.legend}>Required agreements</legend>
          <label className={regStyles.check}>
            <input
              type="checkbox"
              checked={consent.tos}
              onChange={(e) => setConsent({ ...consent, tos: e.target.checked })}
            />
            <span>I accept the Terms of Service</span>
          </label>
          <label className={regStyles.check}>
            <input
              type="checkbox"
              checked={consent.privacy}
              onChange={(e) => setConsent({ ...consent, privacy: e.target.checked })}
            />
            <span>I accept the Privacy Policy</span>
          </label>
          <label className={regStyles.check}>
            <input
              type="checkbox"
              checked={consent.age}
              onChange={(e) => setConsent({ ...consent, age: e.target.checked })}
            />
            <span>I am at least 13 years old</span>
          </label>
        </fieldset>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button type="submit" disabled={loading || !allConsented}>
          {loading ? "Creating account\u2026" : "Create account"}
        </button>
      </form>

      <p className={styles.footer}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </main>
  );
}
