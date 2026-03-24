import { useState } from "react";
import { resendVerification } from "../api/auth";
import { useToast } from "../contexts/ToastContext";
import styles from "./VerificationBanner.module.css";

export default function VerificationBanner() {
  const { addToast } = useToast();
  const [sending, setSending] = useState(false);

  const handleResend = async () => {
    setSending(true);
    try {
      await resendVerification();
      addToast("Verification email sent!", "success");
    } catch {
      addToast("Could not send email. Try again later.", "error");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={styles.banner} role="alert">
      <span>Please verify your email to get full access.</span>
      <button
        className={styles.resend}
        onClick={handleResend}
        disabled={sending}
      >
        {sending ? "Sending\u2026" : "Resend email"}
      </button>
    </div>
  );
}
