import { useEffect, useState } from "react";
import { useRegisterSW } from "virtual:pwa-register/react";
import styles from "./UpdatePrompt.module.css";

export default function UpdatePrompt() {
  const [show, setShow] = useState(false);

  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(swUrl, registration) {
      // Check for updates every 60 minutes
      if (registration) {
        setInterval(() => {
          registration.update();
        }, 60 * 60 * 1000);
      }
    },
  });

  useEffect(() => {
    if (needRefresh) setShow(true);
  }, [needRefresh]);

  if (!show) return null;

  return (
    <div className={styles.banner} role="alert">
      <span className={styles.text}>A new version is available</span>
      <button
        className={styles.updateBtn}
        onClick={() => updateServiceWorker(true)}
      >
        Update
      </button>
      <button
        className={styles.dismissBtn}
        onClick={() => setShow(false)}
        aria-label="Dismiss"
      >
        &times;
      </button>
    </div>
  );
}
