import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import RelativeTime from "./ui/RelativeTime";
import styles from "./NotificationItem.module.css";

const TYPE_CONFIG = {
  follow:        { text: "followed you",                         link: (n) => `/u/${n.actor_username}` },
  new_comment:   { text: "commented on your post",               link: (n) => `/posts/${n.post_id}` },
  reply:         { text: "replied to your comment",              link: (n) => `/posts/${n.post_id}` },
  vote:          { text: "voted on your post",                   link: (n) => `/posts/${n.post_id}` },
  share:         { text: "shared your post",                     link: (n) => `/posts/${n.post_id}` },
  mention:       { text: "mentioned you",                        link: (n) => `/posts/${n.post_id}` },
  community_join:{ text: "joined your community",                link: (n) => n.community_id ? `/communities` : null },
  mod_promote:   { text: "promoted you to moderator",            link: (n) => null },
  mod_demote:    { text: "changed your moderator role",          link: (n) => null },
  ban_proposal:  { text: "proposed a ban",                       link: (n) => null },
  ban_appeal:    { text: "appealed a ban",                       link: (n) => null },
  ban_resolved:  { text: "ban resolved",                         link: (n) => null },
  story_report:  { text: "reported a story",                     link: (n) => null },
  welcome:       { text: "Welcome to PimPam!",                   link: () => "/" },
};

export default function NotificationItem({ notification, onRead }) {
  const n = notification;
  const config = TYPE_CONFIG[n.type] || { text: n.type, link: () => null };
  const href = config.link(n);
  const groupText = n.group_count > 1 ? ` and ${n.group_count - 1} other${n.group_count > 2 ? "s" : ""}` : "";

  const handleClick = () => {
    if (!n.is_read) onRead?.(n.id);
  };

  const content = (
    <div className={`${styles.item} ${n.is_read ? "" : styles.unread}`}>
      <Avatar
        src={n.actor_avatar_url}
        alt={n.actor_username ? `@${n.actor_username}` : "System"}
        size={36}
      />
      <div className={styles.body}>
        <p className={styles.text}>
          {n.actor_username && <strong>@{n.actor_username}</strong>}
          {groupText} {config.text}
        </p>
        <RelativeTime date={n.created_at} />
      </div>
      {!n.is_read && <span className={styles.dot} />}
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
