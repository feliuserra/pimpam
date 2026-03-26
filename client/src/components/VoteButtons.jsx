import { useState } from "react";
import ArrowUpIcon from "./ui/icons/ArrowUpIcon";
import ArrowDownIcon from "./ui/icons/ArrowDownIcon";
import * as postsApi from "../api/posts";
import styles from "./VoteButtons.module.css";

export default function VoteButtons({ postId, karma, userVote, onKarmaChange }) {
  const [optimisticVote, setOptimisticVote] = useState(userVote);
  const [optimisticKarma, setOptimisticKarma] = useState(karma);
  const [busy, setBusy] = useState(false);

  const handleVote = async (direction) => {
    if (busy) return;

    const prevVote = optimisticVote;
    const prevKarma = optimisticKarma;

    if (optimisticVote === direction) {
      // Retract vote
      setOptimisticVote(null);
      setOptimisticKarma(optimisticKarma - direction);
      setBusy(true);
      try {
        await postsApi.retractVote(postId);
        onKarmaChange?.(optimisticKarma - direction, null);
      } catch {
        setOptimisticVote(prevVote);
        setOptimisticKarma(prevKarma);
      } finally {
        setBusy(false);
      }
    } else {
      // Cast or change vote
      const delta = optimisticVote ? direction - optimisticVote : direction;
      setOptimisticVote(direction);
      setOptimisticKarma(optimisticKarma + delta);
      setBusy(true);
      try {
        await postsApi.vote(postId, direction);
        onKarmaChange?.(optimisticKarma + delta, direction);
      } catch {
        setOptimisticVote(prevVote);
        setOptimisticKarma(prevKarma);
      } finally {
        setBusy(false);
      }
    }
  };

  return (
    <div className={styles.votes}>
      <button
        className={`${styles.voteBtn} ${optimisticVote === 1 ? styles.upvoted : ""}`}
        onClick={() => handleVote(1)}
        aria-label="Upvote"
        disabled={busy}
      >
        <ArrowUpIcon size={18} />
      </button>
      <span className={styles.karma}>{optimisticKarma}</span>
      <button
        className={`${styles.voteBtn} ${optimisticVote === -1 ? styles.downvoted : ""}`}
        onClick={() => handleVote(-1)}
        aria-label="Downvote"
        disabled={busy}
      >
        <ArrowDownIcon size={18} />
      </button>
    </div>
  );
}
