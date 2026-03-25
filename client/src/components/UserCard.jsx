import { useState } from "react";
import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";
import styles from "./UserCard.module.css";

export default function UserCard({ user, hideFollow = false, isCloseFriend = false }) {
  const { user: me } = useAuth();
  const [following, setFollowing] = useState(user.is_following);
  const [busy, setBusy] = useState(false);

  const isSelf = me && me.id === user.id;

  const toggleFollow = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (following) {
        await usersApi.unfollow(user.username);
        setFollowing(false);
      } else {
        await usersApi.follow(user.username);
        setFollowing(true);
      }
    } catch {
      // silent
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.card}>
      <Link to={`/u/${user.username}`} className={styles.info}>
        <Avatar src={user.avatar_url} alt={`@${user.username}`} size={40} />
        <div>
          <span className={styles.name}>
            {isCloseFriend && <span className={styles.star} aria-label="Close friend">★</span>}
            {user.display_name || `@${user.username}`}
          </span>
          <span className={styles.username}>@{user.username}</span>
        </div>
      </Link>
      {me && !isSelf && !hideFollow && (
        <button
          className={`${styles.followBtn} ${following ? styles.following : ""}`}
          onClick={toggleFollow}
          disabled={busy}
        >
          {following ? "Following" : "Follow"}
        </button>
      )}
    </div>
  );
}
