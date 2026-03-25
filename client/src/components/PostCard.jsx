import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import Avatar from "./ui/Avatar";
import RelativeTime from "./ui/RelativeTime";
import VoteButtons from "./VoteButtons";
import ShareModal from "./ShareModal";
import CommentIcon from "./ui/icons/CommentIcon";
import ShareIcon from "./ui/icons/ShareIcon";
import BoostIcon from "./ui/icons/BoostIcon";
import MoreIcon from "./ui/icons/MoreIcon";
import ExternalLinkIcon from "./ui/icons/ExternalLinkIcon";
import LinkPreview from "./LinkPreview";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import * as postsApi from "../api/posts";
import styles from "./PostCard.module.css";

const EDIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

export default function PostCard({ post, onDelete, onUpdate, isCloseFriend = false, showPinAction = false, isPinned = false, onPin, onUnpin }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const [menuOpen, setMenuOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const menuRef = useRef(null);

  const isAuthor = user && post.author_id === user.id;
  const canEdit =
    isAuthor && Date.now() - new Date(post.created_at).getTime() < EDIT_WINDOW_MS;

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleDelete = async () => {
    setMenuOpen(false);
    if (!window.confirm("Delete this post?")) return;
    try {
      await postsApi.remove(post.id);
      onDelete?.(post.id);
    } catch {
      // silent — toast could be added later
    }
  };

  const handleBoost = async () => {
    try {
      await postsApi.boost(post.id);
      addToast("Post boosted!", "success");
    } catch (err) {
      const status = err.response?.status;
      if (status === 400) {
        addToast("Only federated posts can be boosted", "error");
      } else if (status === 503) {
        addToast("Federation is not enabled", "error");
      } else {
        addToast("Failed to boost", "error");
      }
    }
  };

  // Shared-from header
  const isShare = post.shared_from_id != null;

  return (
    <article className={styles.card}>
      {/* Share header */}
      {isShare && (
        <div className={styles.shareHeader}>
          <ShareIcon size={14} />
          <span>
            <Link to={`/u/${post.author_username}`}>
              @{post.author_username}
            </Link>{" "}
            shared
          </span>
        </div>
      )}

      {/* Share comment */}
      {isShare && post.share_comment && (
        <p className={styles.shareComment}>{post.share_comment}</p>
      )}

      {/* Author row */}
      <div className={styles.authorRow}>
        <Link to={`/u/${post.author_username}`} className={styles.authorLink}>
          <Avatar
            src={post.author_avatar_url}
            alt={`@${post.author_username}`}
            size={32}
          />
          <span className={styles.authorName}>
            {isCloseFriend && <span className={styles.closeStar} aria-label="Close friend">★</span>}
            @{post.author_username}
          </span>
        </Link>

        {post.community_name && (
          <>
            <span className={styles.separator}>in</span>
            <Link
              to={`/c/${post.community_name}`}
              className={styles.communityBadge}
            >
              c/{post.community_name}
            </Link>
          </>
        )}

        <span className={styles.dot}>·</span>
        <RelativeTime date={post.created_at} />

        {post.is_edited && (
          <span className={styles.edited} title={post.edited_at ? `Edited ${new Date(post.edited_at).toLocaleString()}` : "Edited"}>
            (edited)
          </span>
        )}
      </div>

      {/* Title */}
      <h2 className={styles.title}>
        {post.url ? (
          <a href={post.url} target="_blank" rel="noopener noreferrer">
            {post.title}
            <ExternalLinkIcon size={14} />
          </a>
        ) : (
          <Link to={`/posts/${post.id}`}>{post.title}</Link>
        )}
      </h2>

      {/* Content (truncated) */}
      {post.content && (
        <p className={styles.content}>{post.content}</p>
      )}

      {/* Hashtags */}
      {post.hashtags && post.hashtags.length > 0 && (
        <div className={styles.hashtags}>
          {post.hashtags.map((tag) => (
            <Link key={tag} to={`/tag/${tag}`} className={styles.hashtagPill}>
              #{tag}
            </Link>
          ))}
        </div>
      )}

      {/* Link preview */}
      {post.url && <LinkPreview url={post.url} />}

      {/* Images */}
      {post.images && post.images.length > 0 && (
        <Link to={`/posts/${post.id}`} className={styles.imageContainer}>
          <img
            src={post.images[0].url}
            alt=""
            className={styles.image}
            loading="lazy"
          />
          {post.images.length > 1 && (
            <span className={styles.imageBadge}>+{post.images.length - 1}</span>
          )}
        </Link>
      )}

      {/* Single image fallback */}
      {(!post.images || post.images.length === 0) && post.image_url && (
        <Link to={`/posts/${post.id}`} className={styles.imageContainer}>
          <img
            src={post.image_url}
            alt=""
            className={styles.image}
            loading="lazy"
          />
        </Link>
      )}

      {/* Action bar */}
      <div className={styles.actions}>
        <VoteButtons
          postId={post.id}
          karma={post.karma}
          userVote={post.user_vote}
          onKarmaChange={(newKarma, newVote) =>
            onUpdate?.({ ...post, karma: newKarma, user_vote: newVote })
          }
        />

        <Link to={`/posts/${post.id}`} className={styles.actionBtn}>
          <CommentIcon size={18} />
          {post.comment_count > 0 && (
            <span className={styles.actionCount}>{post.comment_count}</span>
          )}
        </Link>

        <button className={styles.actionBtn} aria-label="Share" onClick={() => {
          if (navigator.share) {
            navigator.share({
              title: post.title,
              url: `${window.location.origin}/posts/${post.id}`,
            }).catch(() => {});
          } else {
            setShareOpen(true);
          }
        }}>
          <ShareIcon size={18} />
        </button>

        <button className={styles.actionBtn} aria-label="Boost" onClick={handleBoost}>
          <BoostIcon size={18} />
        </button>

        {/* Overflow menu */}
        {isAuthor && (
          <div className={styles.menuWrapper} ref={menuRef}>
            <button
              className={styles.actionBtn}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="More options"
              aria-expanded={menuOpen}
            >
              <MoreIcon size={18} />
            </button>
            {menuOpen && (
              <div className={styles.menu} role="menu">
                {showPinAction && !isPinned && (
                  <button
                    className={styles.menuItem}
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); onPin?.(); }}
                  >
                    Pin to profile
                  </button>
                )}
                {showPinAction && isPinned && (
                  <button
                    className={styles.menuItem}
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); onUnpin?.(); }}
                  >
                    Unpin from profile
                  </button>
                )}
                {canEdit && (
                  <Link
                    to={`/posts/${post.id}`}
                    className={styles.menuItem}
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    Edit
                  </Link>
                )}
                <button
                  className={`${styles.menuItem} ${styles.danger}`}
                  role="menuitem"
                  onClick={handleDelete}
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Visibility indicator */}
      {post.visibility === "group" && (
        <div className={styles.visibilityTag}>Friends only</div>
      )}
      <ShareModal
        open={shareOpen}
        onClose={() => setShareOpen(false)}
        postId={post.shared_from_id || post.id}
      />
    </article>
  );
}
