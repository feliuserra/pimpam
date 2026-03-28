import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import styles from "./MessageBubble.module.css";

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

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

export default function MessageBubble({ message, isOwn, onDelete, grouped, hasNext }) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);
  const hasSharedPost = message.shared_post != null;

  // Close menu on outside click
  useEffect(() => {
    if (!showMenu) return;
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showMenu]);

  // Check if message is within 1 hour (deletable)
  const canDelete =
    onDelete && Date.now() - new Date(message.created_at).getTime() < 3600000;

  const handleContextMenu = (e) => {
    if (!canDelete) return;
    e.preventDefault();
    setShowMenu(true);
  };

  // Tombstone for deleted messages
  if (message.is_deleted) {
    return (
      <div className={`${styles.row} ${isOwn ? styles.own : styles.theirs}`}>
        <div className={styles.tombstone}>
          <p className={styles.tombstoneText}>This message was deleted</p>
          <span className={styles.time}>
            {timeFormatter.format(new Date(message.created_at))}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${styles.row} ${isOwn ? styles.own : styles.theirs}`}
      onContextMenu={handleContextMenu}
    >
      <div className={`${styles.bubble} ${isOwn ? styles.ownBubble : styles.theirBubble} ${grouped ? styles.grouped : ""} ${hasNext ? styles.hasNext : ""}`}>
        {hasSharedPost && (
          <SharedPostCard post={message.shared_post} isOwn={isOwn} />
        )}
        <p className={styles.text}>{message.ciphertext}</p>
        <span className={styles.time}>
          {timeFormatter.format(new Date(message.created_at))}
          {isOwn && (
            <span className={message.is_read ? styles.readCheck : styles.sentCheck}>
              {message.is_read ? " ✓✓" : " ✓"}
            </span>
          )}
        </span>
      </div>
      {showMenu && (
        <div className={styles.contextMenu} ref={menuRef}>
          <button
            className={styles.contextMenuItem}
            onClick={() => {
              setShowMenu(false);
              onDelete();
            }}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}
