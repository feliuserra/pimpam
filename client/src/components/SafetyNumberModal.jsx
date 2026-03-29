import { useState, useEffect } from "react";
import Modal from "./ui/Modal";
import Spinner from "./ui/Spinner";
import { computeFingerprint, computeSafetyNumber } from "../crypto/fingerprint";
import { saveVerification, getVerification, clearVerification } from "../crypto/verification";
import styles from "./SafetyNumberModal.module.css";

/**
 * Safety number modal for verifying a contact's encryption key.
 *
 * @param {boolean} open
 * @param {function} onClose
 * @param {string} myPublicKey — base64 SPKI of current user's device
 * @param {string} theirPublicKey — base64 SPKI of contact's device
 * @param {number} contactUserId
 * @param {string} contactUsername
 * @param {function} onVerificationChange — called with { verified, fingerprint }
 */
export default function SafetyNumberModal({
  open,
  onClose,
  myPublicKey,
  theirPublicKey,
  contactUserId,
  contactUsername,
  onVerificationChange,
}) {
  const [safetyNumber, setSafetyNumber] = useState("");
  const [myFp, setMyFp] = useState("");
  const [theirFp, setTheirFp] = useState("");
  const [verified, setVerified] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open || !myPublicKey || !theirPublicKey) return;
    let cancelled = false;

    async function compute() {
      setLoading(true);
      const [mfp, tfp] = await Promise.all([
        computeFingerprint(myPublicKey),
        computeFingerprint(theirPublicKey),
      ]);
      if (cancelled) return;
      setMyFp(mfp);
      setTheirFp(tfp);

      const sn = await computeSafetyNumber(mfp, tfp);
      if (cancelled) return;
      setSafetyNumber(sn);

      // Check if already verified with this fingerprint
      const stored = await getVerification(contactUserId);
      if (cancelled) return;
      setVerified(stored?.fingerprint === tfp);
      setLoading(false);
    }

    compute();
    return () => { cancelled = true; };
  }, [open, myPublicKey, theirPublicKey, contactUserId]);

  const handleToggleVerified = async () => {
    if (verified) {
      await clearVerification(contactUserId);
      setVerified(false);
      onVerificationChange?.({ verified: false, fingerprint: theirFp });
    } else {
      await saveVerification(contactUserId, theirFp);
      setVerified(true);
      onVerificationChange?.({ verified: true, fingerprint: theirFp });
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Verify encryption">
      {loading ? (
        <div className={styles.loader}><Spinner size={24} /></div>
      ) : (
        <div className={styles.content}>
          <p className={styles.instructions}>
            Compare this number with <strong>@{contactUsername}</strong> via a
            trusted channel (in person, phone call, etc).
          </p>

          <div className={styles.safetyNumber} aria-label="Safety number">
            {safetyNumber}
          </div>

          <div className={styles.fingerprints}>
            <div className={styles.fpBlock}>
              <span className={styles.fpLabel}>Your fingerprint</span>
              <span className={styles.fpValue}>{myFp}</span>
            </div>
            <div className={styles.fpBlock}>
              <span className={styles.fpLabel}>@{contactUsername}</span>
              <span className={styles.fpValue}>{theirFp}</span>
            </div>
          </div>

          <button
            className={`${styles.verifyBtn} ${verified ? styles.verified : ""}`}
            onClick={handleToggleVerified}
          >
            {verified ? "Unmark as verified" : "Mark as verified"}
          </button>
        </div>
      )}
    </Modal>
  );
}
