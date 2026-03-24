import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmail } from "../api/auth";
import Spinner from "../components/ui/Spinner";
import styles from "./Auth.module.css";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [status, setStatus] = useState("loading"); // loading | success | error
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }
    verifyEmail(token)
      .then(() => {
        setStatus("success");
        setMessage("Email verified. You now have full access.");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.response?.data?.detail ?? "Verification failed. The link may have expired.");
      });
  }, [token]);

  return (
    <main className={styles.container}>
      <h1 className={styles.logo}>PimPam</h1>

      {status === "loading" && (
        <div style={{ display: "flex", justifyContent: "center", marginTop: "2rem" }}>
          <Spinner size={32} />
        </div>
      )}

      {status === "success" && (
        <>
          <h2 style={{ fontSize: "1.25rem", marginTop: "1rem", color: "#16a34a" }}>
            Verified!
          </h2>
          <p style={{ color: "var(--text-secondary)", marginTop: "0.5rem" }}>{message}</p>
          <p className={styles.footer}>
            <Link to="/login">Sign in</Link>
          </p>
        </>
      )}

      {status === "error" && (
        <>
          <p className={styles.error} role="alert" style={{ marginTop: "1.5rem" }}>
            {message}
          </p>
          <p className={styles.footer}>
            <Link to="/login">Back to sign in</Link>
          </p>
        </>
      )}
    </main>
  );
}
