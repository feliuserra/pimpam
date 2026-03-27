import { Link } from "react-router-dom";
import RelativeTime from "./ui/RelativeTime";
import styles from "./MessageBubble.module.css";

function SharedPostCard({ post, isOwn }) {
  return (
    <Link
      to={`/posts/${post.id}`}
      className={`${styles.sharedCard} ${isOwn ? styles.sharedCardOwn : ""}`}
    >
      {post.image_url && (
        <img className={styles.sharedImg} src={post.image_url} alt="" />
      )}
      <div className={styles.sharedBody}>
        <span className={styles.sharedTitle}>{post.title}</span>
        <span className={styles.sharedMeta}>
          {post.author_username && `@${post.author_username}`}
          {post.community_name && ` in c/${post.community_name}`}
        </span>
        {post.content && (
          <span className={styles.sharedSnippet}>{post.content}</span>
        )}
      </div>
    </Link>
  );
}

export default function MessageBubble({ message, isOwn }) {
  const hasSharedPost = message.shared_post != null;

  return (
    <div className={`${styles.row} ${isOwn ? styles.own : styles.theirs}`}>
      <div className={`${styles.bubble} ${isOwn ? styles.ownBubble : styles.theirBubble}`}>
        {hasSharedPost && (
          <SharedPostCard post={message.shared_post} isOwn={isOwn} />
        )}
        <p className={styles.text}>{message.ciphertext}</p>
        <span className={styles.time}>
          <RelativeTime date={message.created_at} />
          {isOwn && message.is_read && <span className={styles.read}> ✓</span>}
        </span>
      </div>
    </div>
  );
}
