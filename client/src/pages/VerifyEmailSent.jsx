import { Link } from "react-router-dom";
import styles from "./Auth.module.css";

export default function VerifyEmailSent() {
  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>
      <h2 style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>Check your email</h2>
      <p style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
        We sent a verification link to the email address you provided.
        Click the link to activate your account.
      </p>
      <p style={{ color: "var(--text-secondary)", marginTop: "1rem", fontSize: "0.875rem" }}>
        Didn't get the email? Check your spam folder or{" "}
        <Link to="/login">sign in</Link> to resend it.
      </p>
    </main>
  );
}
