import { useState } from "react";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

export default function RemovedContent({ communityName }) {
  const [postId, setPostId] = useState("");
  const [commentId, setCommentId] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const handleRestorePost = async (e) => {
    e.preventDefault();
    if (!postId.trim() || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await modApi.restorePost(communityName, postId.trim());
      setStatus({ type: "success", msg: `Post ${postId} restored.` });
      setPostId("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to restore post" });
    } finally {
      setBusy(false);
    }
  };

  const handleRemovePost = async (e) => {
    e.preventDefault();
    if (!postId.trim() || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await modApi.removePost(communityName, postId.trim());
      setStatus({ type: "success", msg: `Post ${postId} removed.` });
      setPostId("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to remove post" });
    } finally {
      setBusy(false);
    }
  };

  const handleRestoreComment = async (e) => {
    e.preventDefault();
    if (!commentId.trim() || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await modApi.restoreComment(communityName, commentId.trim());
      setStatus({ type: "success", msg: `Comment ${commentId} restored.` });
      setCommentId("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to restore comment" });
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveComment = async (e) => {
    e.preventDefault();
    if (!commentId.trim() || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      await modApi.removeComment(communityName, commentId.trim());
      setStatus({ type: "success", msg: `Comment ${commentId} removed.` });
      setCommentId("");
    } catch (err) {
      setStatus({ type: "error", msg: err.response?.data?.detail || "Failed to remove comment" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      {status && (
        <p className={status.type === "error" ? styles.error : styles.success} role="alert">
          {status.msg}
        </p>
      )}

      <section className={styles.section}>
        <h3 className={styles.heading}>Posts</h3>
        <form className={styles.inlineForm} onSubmit={handleRestorePost}>
          <input
            className={styles.input}
            value={postId}
            onChange={(e) => setPostId(e.target.value)}
            placeholder="Post ID"
            type="number"
          />
          <button type="submit" className={styles.btn} disabled={busy || !postId.trim()}>
            Restore
          </button>
          <button type="button" className={styles.dangerBtn} disabled={busy || !postId.trim()} onClick={handleRemovePost}>
            Remove
          </button>
        </form>
      </section>

      <section className={styles.section}>
        <h3 className={styles.heading}>Comments</h3>
        <form className={styles.inlineForm} onSubmit={handleRestoreComment}>
          <input
            className={styles.input}
            value={commentId}
            onChange={(e) => setCommentId(e.target.value)}
            placeholder="Comment ID"
            type="number"
          />
          <button type="submit" className={styles.btn} disabled={busy || !commentId.trim()}>
            Restore
          </button>
          <button type="button" className={styles.dangerBtn} disabled={busy || !commentId.trim()} onClick={handleRemoveComment}>
            Remove
          </button>
        </form>
      </section>
    </div>
  );
}
