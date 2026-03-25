import styles from "./Offline.module.css";

export default function Offline() {
  return (
    <div className={styles.container}>
      <h1 className={styles.heading}>You appear to be offline</h1>
      <p className={styles.text}>
        Check your internet connection and try again.
      </p>
      <button
        className={styles.retryBtn}
        onClick={() => window.location.reload()}
      >
        Retry
      </button>
    </div>
  );
}
