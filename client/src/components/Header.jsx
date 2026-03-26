import styles from "./Header.module.css";

export default function Header({ left, right }) {
  return (
    <header className={styles.header}>
      <div className={styles.left}>{left}</div>
      <div className={styles.right}>{right}</div>
    </header>
  );
}
