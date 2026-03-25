import RelativeTime from "./ui/RelativeTime";
import styles from "./MessageBubble.module.css";

export default function MessageBubble({ message, isOwn }) {
  return (
    <div className={`${styles.row} ${isOwn ? styles.own : styles.theirs}`}>
      <div className={`${styles.bubble} ${isOwn ? styles.ownBubble : styles.theirBubble}`}>
        <p className={styles.text}>{message.ciphertext}</p>
        <span className={styles.time}>
          <RelativeTime date={message.created_at} />
          {isOwn && message.is_read && <span className={styles.read}> ✓</span>}
        </span>
      </div>
    </div>
  );
}
