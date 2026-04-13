import { useState } from "react";
import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import RelativeTime from "./ui/RelativeTime";
import MarkdownContent from "./MarkdownContent";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import errorMessage from "../api/errorMessage";
import * as commentsApi from "../api/comments";
import styles from "./CommentCard.module.css";

const REACTION_LABELS = {
  agree: "Agree",
  love: "Love",
  misleading: "Misleading",
  disagree: "Disagree",
};

const MAX_VISIBLE_DEPTH = 4;

export default function CommentCard({ comment, onReply, onDeleted }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [replies, setReplies] = useState(null);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reactionCounts, setReactionCounts] = useState(comment.reaction_counts || {});
  const [myReaction, setMyReaction] = useState(comment.user_reaction || null);

  const isAuthor = user && comment.author_id === user.id;
  const isDeleted = comment.is_removed;
  const canNest = comment.depth < MAX_VISIBLE_DEPTH;

  const handleLoadReplies = async () => {
    setLoadingReplies(true);
    try {
      const res = await commentsApi.listReplies(comment.id);
      setReplies(res.data);
    } catch {
      // silent
    } finally {
      setLoadingReplies(false);
    }
  };

  const handleSubmitReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await commentsApi.create(comment.post_id, {
        content: replyText.trim(),
        parent_id: comment.id,
      });
      // Add the new reply locally
      setReplies((prev) => (prev ? [...prev, res.data] : [res.data]));
      setReplyText("");
      setShowReplyInput(false);
      onReply?.(res.data);
    } catch (err) {
      addToast(errorMessage(err, "Couldn't post your reply. Try again."), "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this comment?")) return;
    try {
      await commentsApi.remove(comment.id);
      onDeleted?.(comment.id);
    } catch {
      // silent
    }
  };

  const handleReact = async (type) => {
    if (!user) return;
    const wasActive = myReaction === type;
    const prevCounts = { ...reactionCounts };
    const prevReaction = myReaction;

    // Optimistic update
    if (wasActive) {
      setMyReaction(null);
      setReactionCounts((c) => ({ ...c, [type]: Math.max(0, (c[type] || 0) - 1) }));
    } else {
      // Remove old reaction count if switching
      if (myReaction) {
        setReactionCounts((c) => ({ ...c, [myReaction]: Math.max(0, (c[myReaction] || 0) - 1) }));
      }
      setMyReaction(type);
      setReactionCounts((c) => ({ ...c, [type]: (c[type] || 0) + 1 }));
    }

    try {
      if (wasActive) {
        await commentsApi.removeReaction(comment.id, type);
      } else {
        // Remove old reaction on backend before adding new one
        if (prevReaction) {
          await commentsApi.removeReaction(comment.id, prevReaction);
        }
        await commentsApi.react(comment.id, type);
      }
    } catch {
      // Revert on error
      setReactionCounts(prevCounts);
      setMyReaction(prevReaction);
    }
  };

  return (
    <div
      className={styles.wrapper}
      style={{ "--depth": comment.depth }}
    >
      <div className={styles.card}>
        {/* Author row */}
        <div className={styles.header}>
          {!isDeleted ? (
            <>
              <Link to={`/u/${comment.author_username}`} className={styles.authorLink}>
                <Avatar
                  src={comment.author_avatar_url}
                  alt={`@${comment.author_username}`}
                  size={24}
                />
                <span className={styles.authorName}>@{comment.author_username}</span>
              </Link>
              <span className={styles.dot}>·</span>
              <RelativeTime date={comment.created_at} />
            </>
          ) : (
            <span className={styles.deleted}>[deleted]</span>
          )}
        </div>

        {/* Content */}
        {!isDeleted && (
          <MarkdownContent as="p" className={styles.content}>{comment.content}</MarkdownContent>
        )}

        {/* Actions */}
        {!isDeleted && (
          <div className={styles.actions}>
            {/* Reactions */}
            {Object.entries(REACTION_LABELS).map(([type, label]) => {
              const count = reactionCounts[type] || 0;
              const isActive = myReaction === type;
              return (
                <button
                  key={type}
                  className={`${styles.reactionBtn} ${isActive ? styles.reactionActive : ""}`}
                  onClick={() => handleReact(type)}
                  title={label}
                  disabled={!user}
                >
                  {label}
                  {count > 0 && <span className={styles.reactionCount}>{count}</span>}
                </button>
              );
            })}

            {/* Reply */}
            {user && canNest && (
              <button
                className={styles.replyBtn}
                onClick={() => setShowReplyInput(!showReplyInput)}
              >
                Reply
              </button>
            )}

            {/* Delete */}
            {isAuthor && (
              <button className={styles.deleteBtn} onClick={handleDelete}>
                Delete
              </button>
            )}
          </div>
        )}

        {/* Reply input */}
        {showReplyInput && (
          <form className={styles.replyForm} onSubmit={handleSubmitReply}>
            <input
              className={styles.replyInput}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder="Write a reply..."
              maxLength={300}
              autoFocus
            />
            <button
              type="submit"
              className={styles.replySubmit}
              disabled={!replyText.trim() || submitting}
            >
              {submitting ? "..." : "Reply"}
            </button>
          </form>
        )}
      </div>

      {/* Load replies button */}
      {comment.reply_count > 0 && replies === null && (
        <button
          className={styles.loadReplies}
          onClick={handleLoadReplies}
          disabled={loadingReplies}
        >
          {loadingReplies
            ? "Loading..."
            : `Load ${comment.reply_count} ${comment.reply_count === 1 ? "reply" : "replies"}`}
        </button>
      )}

      {/* Nested replies */}
      {replies && replies.length > 0 && (
        <div className={styles.replies}>
          {replies.map((reply) => (
            <CommentCard
              key={reply.id}
              comment={reply}
              onReply={onReply}
              onDeleted={(id) =>
                setReplies((prev) =>
                  prev.map((r) =>
                    r.id === id ? { ...r, is_removed: true, content: "[deleted]" } : r,
                  ),
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
