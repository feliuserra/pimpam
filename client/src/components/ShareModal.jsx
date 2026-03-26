import { useState, useEffect } from "react";
import Modal from "./ui/Modal";
import Spinner from "./ui/Spinner";
import { useToast } from "../contexts/ToastContext";
import * as postsApi from "../api/posts";
import * as communitiesApi from "../api/communities";
import styles from "./ShareModal.module.css";

export default function ShareModal({ open, onClose, postId }) {
  const { addToast } = useToast();
  const [comment, setComment] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [communities, setCommunities] = useState([]);
  const [sharing, setSharing] = useState(false);

  const handleCopyLink = () => {
    const url = `${window.location.origin}/posts/${postId}`;
    navigator.clipboard.writeText(url).then(
      () => addToast("Link copied!", "success"),
      () => addToast("Failed to copy link", "error"),
    );
  };

  useEffect(() => {
    if (!open) return;
    setComment("");
    setCommunityId("");
    communitiesApi.listJoined().then((res) => {
      setCommunities(res.data);
    }).catch(() => {});
  }, [open]);

  const handleShare = async (e) => {
    e.preventDefault();
    if (sharing) return;
    setSharing(true);
    try {
      const data = {};
      if (comment.trim()) data.comment = comment.trim();
      if (communityId) data.community_id = Number(communityId);
      await postsApi.share(postId, data);
      addToast("Post shared!", "success");
      onClose();
    } catch (err) {
      const code = err.response?.data?.detail;
      if (typeof code === "string" && code.includes("already_shared")) {
        addToast("You already shared this post", "error");
      } else {
        addToast("Failed to share", "error");
      }
    } finally {
      setSharing(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Share post">
      <form className={styles.form} onSubmit={handleShare}>
        <textarea
          className={styles.comment}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment (optional)"
          maxLength={300}
          rows={3}
        />

        <label className={styles.label}>
          Share to community (optional)
          <select
            className={styles.select}
            value={communityId}
            onChange={(e) => setCommunityId(e.target.value)}
          >
            <option value="">Your profile</option>
            {communities.map((c) => (
              <option key={c.id} value={c.id}>
                c/{c.name}
              </option>
            ))}
          </select>
        </label>

        <div className={styles.actions}>
          <button className={styles.copyBtn} type="button" onClick={handleCopyLink}>
            Copy link
          </button>
          <button className={styles.submitBtn} type="submit" disabled={sharing}>
            {sharing ? <Spinner size={16} /> : "Share"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
