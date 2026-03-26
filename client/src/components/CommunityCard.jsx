import { useState } from "react";
import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import CheckIcon from "./ui/icons/CheckIcon";
import { useAuth } from "../contexts/AuthContext";
import * as communitiesApi from "../api/communities";
import styles from "./CommunityCard.module.css";

export default function CommunityCard({ community, isJoined, onJoinChange }) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [joined, setJoined] = useState(isJoined || false);

  const handleToggle = async (e) => {
    e.preventDefault();
    if (busy || !user) return;
    setBusy(true);
    try {
      if (joined) {
        await communitiesApi.leave(community.name);
        setJoined(false);
        onJoinChange?.(community.id, false);
      } else {
        await communitiesApi.join(community.name);
        setJoined(true);
        onJoinChange?.(community.id, true);
      }
    } catch (err) {
      if (err?.response?.status === 409) {
        setJoined(!joined);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <Link to={`/c/${community.name}`} className={styles.card}>
      <Avatar
        src={community.avatar_url}
        alt={community.name}
        size={40}
        className={styles.avatar}
      />
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
          className={`${styles.joinBtn} ${joined ? styles.joined : ""}`}
          onClick={handleToggle}
          disabled={busy}
          aria-label={joined ? "Leave community" : "Join community"}
        >
          {joined ? <CheckIcon size={16} /> : "+"}
        </button>
      )}
    </Link>
  );
}
