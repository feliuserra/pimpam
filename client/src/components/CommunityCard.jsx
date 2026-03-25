import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import * as communitiesApi from "../api/communities";
import styles from "./CommunityCard.module.css";

export default function CommunityCard({ community, onJoinChange }) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);

  const handleJoin = async (e) => {
    e.preventDefault();
    if (busy || !user) return;
    setBusy(true);
    try {
      await communitiesApi.join(community.name);
      onJoinChange?.(community.id, true);
    } catch {
      // silent — 409 means already joined
    } finally {
      setBusy(false);
    }
  };

  return (
    <Link to={`/c/${community.name}`} className={styles.card}>
      <div className={styles.info}>
        <span className={styles.name}>c/{community.name}</span>
        {community.description && (
          <span className={styles.desc}>{community.description}</span>
        )}
        <span className={styles.members}>
          {community.member_count.toLocaleString()} members
        </span>
      </div>
      {user && (
        <button
          className={styles.joinBtn}
          onClick={handleJoin}
          disabled={busy}
        >
          +
        </button>
      )}
    </Link>
  );
}
