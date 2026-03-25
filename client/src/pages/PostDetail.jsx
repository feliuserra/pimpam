import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import RelativeTime from "../components/ui/RelativeTime";
import Spinner from "../components/ui/Spinner";
import VoteButtons from "../components/VoteButtons";
import ImageGallery from "../components/ImageGallery";
import CommentThread from "../components/CommentThread";
import ShareIcon from "../components/ui/icons/ShareIcon";
import BoostIcon from "../components/ui/icons/BoostIcon";
import ExternalLinkIcon from "../components/ui/icons/ExternalLinkIcon";
import { useAuth } from "../contexts/AuthContext";
import * as postsApi from "../api/posts";
import styles from "./PostDetail.module.css";

const EDIT_WINDOW_MS = 60 * 60 * 1000;

export default function PostDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  const loadPost = useCallback(async () => {
    setLoading(true);
    try {
      const res = await postsApi.get(id);
      setPost(res.data);
      setError(null);
    } catch (err) {
      setError(err.response?.status === 404 ? "Post not found" : "Failed to load post");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadPost();
  }, [loadPost]);

  if (loading) {
    return (
      <>
        <Header left={<button onClick={() => navigate(-1)} className={styles.back}>← Back</button>} />
        <div className={styles.loader}><Spinner size={28} /></div>
      </>
    );
  }

  if (error || !post) {
    return (
      <>
        <Header left={<button onClick={() => navigate(-1)} className={styles.back}>← Back</button>} />
        <div className={styles.error}>{error || "Post not found"}</div>
      </>
    );
  }

  const isAuthor = user && post.author_id === user.id;
  const canEdit = isAuthor && Date.now() - new Date(post.created_at).getTime() < EDIT_WINDOW_MS;
  const editTimeLeft = Math.max(0, EDIT_WINDOW_MS - (Date.now() - new Date(post.created_at).getTime()));
  const editMinutesLeft = Math.ceil(editTimeLeft / 60000);

  const handleDelete = async () => {
    if (!window.confirm("Delete this post permanently?")) return;
    try {
      await postsApi.remove(post.id);
      navigate("/", { replace: true });
    } catch {
      // silent
    }
  };

  const handleStartEdit = () => {
    setEditTitle(post.title);
    setEditContent(post.content || "");
    setEditing(true);
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    try {
      const res = await postsApi.edit(post.id, {
        title: editTitle,
        content: editContent || null,
      });
      setPost((prev) => ({ ...prev, ...res.data }));
      setEditing(false);
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const isShare = post.shared_from_id != null;

  // Build images array from post.images or fallback to image_url
  const images =
    post.images && post.images.length > 0
      ? post.images
      : post.image_url
        ? [{ url: post.image_url, display_order: 0 }]
        : [];

  return (
    <>
      <Header
        left={
          <button onClick={() => navigate(-1)} className={styles.back}>
            ← Back
          </button>
        }
      />

      <article className={styles.container}>
        {/* Share header */}
        {isShare && (
          <div className={styles.shareHeader}>
            <ShareIcon size={14} />
            <span>
              <Link to={`/u/${post.author_username}`}>@{post.author_username}</Link> shared
            </span>
          </div>
        )}
        {isShare && post.share_comment && (
          <p className={styles.shareComment}>{post.share_comment}</p>
        )}

        {/* Author row */}
        <div className={styles.authorRow}>
          <Link to={`/u/${post.author_username}`} className={styles.authorLink}>
            <Avatar src={post.author_avatar_url} alt={`@${post.author_username}`} size={36} />
            <div>
              <span className={styles.authorName}>@{post.author_username}</span>
              <RelativeTime date={post.created_at} />
            </div>
          </Link>

          {post.community_name && (
            <Link to={`/c/${post.community_name}`} className={styles.communityBadge}>
              c/{post.community_name}
            </Link>
          )}
        </div>

        {/* Title */}
        {editing ? (
          <form className={styles.editForm} onSubmit={handleSaveEdit}>
            <input
              className={styles.editInput}
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              placeholder="Title"
              required
            />
            <textarea
              className={styles.editTextarea}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              placeholder="Content (optional)"
              rows={5}
            />
            <div className={styles.editActions}>
              <button type="submit" className={styles.saveBtn} disabled={saving}>
                {saving ? "Saving..." : "Save"}
              </button>
              <button type="button" className={styles.cancelBtn} onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <h1 className={styles.title}>
              {post.url ? (
                <a href={post.url} target="_blank" rel="noopener noreferrer">
                  {post.title} <ExternalLinkIcon size={16} />
                </a>
              ) : (
                post.title
              )}
            </h1>

            {post.is_edited && (
              <span className={styles.edited}>
                edited {post.edited_at ? new Date(post.edited_at).toLocaleString() : ""}
              </span>
            )}

            {post.content && <div className={styles.content}>{post.content}</div>}
          </>
        )}

        {/* Images */}
        <ImageGallery images={images} />

        {/* Action bar */}
        <div className={styles.actions}>
          <VoteButtons
            postId={post.id}
            karma={post.karma}
            userVote={post.user_vote}
          />
          <button className={styles.actionBtn} aria-label="Share">
            <ShareIcon size={18} />
            <span>Share</span>
          </button>
          <button className={styles.actionBtn} aria-label="Boost">
            <BoostIcon size={18} />
            <span>Boost</span>
          </button>
        </div>

        {/* Author actions */}
        {isAuthor && !editing && (
          <div className={styles.authorActions}>
            {canEdit && (
              <button className={styles.editBtn} onClick={handleStartEdit}>
                Edit ({editMinutesLeft}m left)
              </button>
            )}
            <button className={styles.deleteBtn} onClick={handleDelete}>
              Delete
            </button>
          </div>
        )}

        {/* Visibility */}
        {post.visibility === "group" && (
          <div className={styles.visibilityTag}>Friends only</div>
        )}

        {/* Comments */}
        <CommentThread postId={post.id} />
      </article>
    </>
  );
}
