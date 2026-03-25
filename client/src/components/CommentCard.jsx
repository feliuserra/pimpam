import { useState } from "react";
import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import RelativeTime from "./ui/RelativeTime";
import { useAuth } from "../contexts/AuthContext";
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
  const [replies, setReplies] = useState(null);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
    } catch {
      // silent
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
    try {
      await commentsApi.react(comment.id, type);
    } catch {
      // 409 = already reacted, ignore
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
          <p className={styles.content}>{comment.content}</p>
        )}

        {/* Actions */}
        {!isDeleted && (
          <div className={styles.actions}>
            {/* Reactions */}
            {Object.entries(REACTION_LABELS).map(([type, label]) => {
              const count = comment.reaction_counts?.[type] || 0;
              return (
                <button
                  key={type}
                  className={styles.reactionBtn}
                  onClick={() => handleReact(type)}
                  title={label}
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
