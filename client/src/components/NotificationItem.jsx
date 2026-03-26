import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import RelativeTime from "./ui/RelativeTime";
import styles from "./NotificationItem.module.css";

const TYPE_CONFIG = {
  follow:        { text: "followed you",                  link: (n) => `/u/${n.actor_username}` },
  new_comment:   { text: "commented on your post",        link: (n) => `/posts/${n.post_id}` },
  reply:         { text: "replied to your comment",       link: (n) => `/posts/${n.post_id}` },
  vote:          { text: "voted on your post",            link: (n) => `/posts/${n.post_id}` },
  share:         { text: "shared your post",              link: (n) => `/posts/${n.post_id}` },
  mention:       { text: "mentioned you",                 link: (n) => `/posts/${n.post_id}` },
  reaction:      { text: "reacted to your comment",       link: (n) => `/posts/${n.post_id}` },
  community_join:{ text: "joined your community",         link: () => `/communities` },
  mod_promote:   { text: "promoted you to moderator",     link: () => null },
  mod_demote:    { text: "changed your moderator role",   link: () => null },
  ban_proposal:  { text: "proposed a ban",                link: () => null },
  ban_appeal:    { text: "appealed a ban",                link: () => null },
  ban_resolved:  { text: "ban resolved",                  link: () => null },
  story_report:  { text: "reported a story",              link: () => null },
  welcome:       { text: "Welcome to PimPam!",            link: () => "/" },
  friend_group_added:   { text: "added you to a friend group",   link: () => null },
  friend_group_removed: { text: "removed you from a friend group", link: () => null },
};

export default function NotificationItem({ notification, onRead, onDismiss, selected, onSelect }) {
  const n = notification;
  const config = TYPE_CONFIG[n.type] || { text: n.type, link: () => null };
  const href = config.link(n);
  const isVote = n.type === "vote";
  const groupText = n.group_count > 1
    ? ` and ${n.group_count - 1} other${n.group_count > 2 ? "s" : ""}`
    : "";

  const handleClick = () => {
    if (!n.is_read) onRead?.(n.id);
  };

  const handleDismiss = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onDismiss?.(n.id);
  };

  const handleSelect = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onSelect?.(n.id);
  };

  const content = (
    <div className={`${styles.item} ${n.is_read ? "" : styles.unread}`}>
      {onSelect && (
        <button
          className={`${styles.checkbox} ${selected ? styles.checked : ""}`}
          onClick={handleSelect}
          aria-label={selected ? "Deselect" : "Select"}
        >
          {selected && "✓"}
        </button>
      )}
      <Avatar
        src={n.actor_avatar_url}
        alt={n.actor_username ? `@${n.actor_username}` : "System"}
        size={36}
      />
      <div className={styles.body}>
        <p className={styles.text}>
          {isVote && n.group_count > 0 && (
            <span className={styles.karmaBadge}>+{n.group_count}</span>
          )}
          {n.actor_username && <strong>@{n.actor_username}</strong>}
          {groupText} {config.text}
        </p>
        <RelativeTime date={n.created_at} />
      </div>
      {!n.is_read && <span className={styles.dot} />}
      {onDismiss && (
        <button
          className={styles.dismissBtn}
          onClick={handleDismiss}
          aria-label="Dismiss notification"
        >
          ×
        </button>
      )}
    </div>
  );

  if (href) {
    return (
      <Link to={href} className={styles.link} onClick={handleClick}>
        {content}
      </Link>
    );
  }

  return (
    <div className={styles.link} onClick={handleClick} role="button" tabIndex={0}>
      {content}
    </div>
  );
}
