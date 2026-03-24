import styles from "./Skeleton.module.css";

export default function Skeleton({ width, height = "1rem", rounded = false }) {
  return (
    <span
      className={`${styles.skeleton} ${rounded ? styles.rounded : ""}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  );
}
