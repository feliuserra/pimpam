import Skeleton from "./ui/Skeleton";
import styles from "./PostCard.module.css";

export default function PostCardSkeleton() {
  return (
    <div className={styles.card} aria-hidden="true">
      <div className={styles.authorRow}>
        <Skeleton width={32} height="32px" rounded />
        <Skeleton width="80px" height="0.8rem" />
        <Skeleton width="40px" height="0.8rem" />
      </div>
      <div style={{ marginBottom: 6 }}>
        <Skeleton width="85%" height="1rem" />
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
        <Skeleton width="100%" height="0.85rem" />
        <Skeleton width="70%" height="0.85rem" />
      </div>
      <div className={styles.actions}>
        <Skeleton width="60px" height="1.5rem" />
        <Skeleton width="40px" height="1.5rem" />
        <Skeleton width="30px" height="1.5rem" />
      </div>
    </div>
  );
}
