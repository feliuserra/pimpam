import { useState, useCallback, useEffect } from "react";
import CommentCard from "./CommentCard";
import Spinner from "./ui/Spinner";
import { useAuth } from "../contexts/AuthContext";
import { useWS } from "../contexts/WSContext";
import * as commentsApi from "../api/comments";
import styles from "./CommentThread.module.css";

export default function CommentThread({ postId }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [sort, setSort] = useState("latest");
  const [loading, setLoading] = useState(true);
  const [newText, setNewText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadComments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await commentsApi.list(postId, { sort, limit: 50 });
      setComments(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [postId, sort]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  // Live append new comments via WS
  useWS(
    "new_comment",
    useCallback(
      (data) => {
        if (data.post_id !== postId || data.parent_id) return;
        // Append the comment stub — it will lack full data but shows up
        setComments((prev) => {
          if (prev.some((c) => c.id === data.comment_id)) return prev;
          return [
            ...prev,
            {
              id: data.comment_id,
              post_id: data.post_id,
              author_id: null,
              author_username: data.author,
              author_avatar_url: null,
              parent_id: null,
              depth: 0,
              content: "",
              is_removed: false,
              created_at: new Date().toISOString(),
              reaction_counts: {},
              reply_count: 0,
              _stub: true,
            },
          ];
        });
        // Re-fetch to get the full comment
        loadComments();
      },
      [postId, loadComments],
    ),
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!newText.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await commentsApi.create(postId, { content: newText.trim() });
      setComments((prev) => [...prev, res.data]);
      setNewText("");
    } catch {
      // silent
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleted = (commentId) => {
    setComments((prev) =>
      prev.map((c) =>
        c.id === commentId ? { ...c, is_removed: true, content: "[deleted]" } : c,
      ),
    );
  };

  return (
    <section className={styles.thread} aria-label="Comments">
      {/* Sort selector */}
      <div className={styles.sortRow}>
        <span className={styles.sortLabel}>Comments</span>
        <select
          className={styles.sortSelect}
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          aria-label="Sort comments"
        >
          <option value="latest">Latest</option>
          <option value="top">Top</option>
        </select>
      </div>

      {/* Comment list */}
      {loading && comments.length === 0 ? (
        <div className={styles.loader}>
          <Spinner size={20} />
        </div>
      ) : comments.length === 0 ? (
        <p className={styles.empty}>No comments yet. Be the first!</p>
      ) : (
        <div className={styles.list}>
          {comments
            .filter((c) => !c._stub)
            .map((comment) => (
              <CommentCard
                key={comment.id}
                comment={comment}
                onDeleted={handleDeleted}
              />
            ))}
        </div>
      )}

      {/* Compose */}
      {user && (
        <form className={styles.compose} onSubmit={handleSubmit}>
          <input
            className={styles.input}
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder="Write a comment..."
            maxLength={300}
          />
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!newText.trim() || submitting}
          >
            {submitting ? "..." : "Post"}
          </button>
        </form>
      )}
    </section>
  );
}
