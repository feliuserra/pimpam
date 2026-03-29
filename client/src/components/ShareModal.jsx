import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "./ui/Modal";
import Spinner from "./ui/Spinner";
import Avatar from "./ui/Avatar";
import InfoTooltip from "./ui/InfoTooltip";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import * as postsApi from "../api/posts";
import * as messagesApi from "../api/messages";
import * as usersApi from "../api/users";
import * as devicesApi from "../api/devices";
import * as communitiesApi from "../api/communities";
import { encryptMessage } from "../crypto/encrypt";
import styles from "./ShareModal.module.css";

export default function ShareModal({ open, onClose, postId, post }) {
  const { user: me } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();
  const [tab, setTab] = useState("send");

  // -- Send to state --
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [dmText, setDmText] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const searchTimeout = useRef(null);

  // -- Reshare state --
  const [comment, setComment] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [communities, setCommunities] = useState([]);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    if (!open) return;
    setTab("send");
    setQuery("");
    setResults([]);
    setSelectedUser(null);
    setDmText("");
    setSending(false);
    setSendError("");
    setComment("");
    setCommunityId("");
    setSharing(false);
    communitiesApi
      .listJoined()
      .then((res) => setCommunities(res.data))
      .catch(() => {});
  }, [open]);

  // User search with debounce
  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      return;
    }
    searchTimeout.current = setTimeout(async () => {
      try {
        const res = await usersApi.autocompleteUsers(query.trim(), 8);
        // Filter out self
        setResults(
          (res.data || []).filter((u) => u.id !== me?.id),
        );
      } catch {
        setResults([]);
      }
    }, 300);
    return () => clearTimeout(searchTimeout.current);
  }, [query, me?.id]);

  const handleSendDM = async (e) => {
    e.preventDefault();
    if (sending || !selectedUser) return;
    setSending(true);
    setSendError("");
    try {
      // Build message text — include post context if no custom text
      const text = dmText.trim() || "Shared a post with you";

      // Fetch recipient and sender device keys for encryption
      const [recipientDkRes, senderDkRes] = await Promise.all([
        devicesApi.getUserDeviceKeys(selectedUser.username),
        devicesApi.getMyDevices(),
      ]);
      const recipientDeviceKeys = recipientDkRes.data;
      const senderDeviceKeys = senderDkRes.data.map((d) => ({
        device_id: d.id,
        public_key: d.public_key,
      }));

      let payload;
      if (recipientDeviceKeys.length > 0) {
        const { ciphertext, deviceKeys } =
          await encryptMessage(text, recipientDeviceKeys, senderDeviceKeys);
        payload = {
          recipient_id: selectedUser.id,
          ciphertext,
          device_keys: deviceKeys,
          shared_post_id: postId,
        };
      } else {
        payload = {
          recipient_id: selectedUser.id,
          ciphertext: text,
          device_keys: [],
          shared_post_id: postId,
        };
      }
      await messagesApi.send(payload);
      addToast(`Sent to @${selectedUser.username}`, "success");
      onClose();
      navigate(`/messages/${selectedUser.id}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail === "Cannot message this user") {
        setSendError("You can't message this user");
      } else {
        setSendError(detail || "Failed to send");
      }
    } finally {
      setSending(false);
    }
  };

  const handleCopyLink = () => {
    const url = `${window.location.origin}/posts/${postId}`;
    navigator.clipboard.writeText(url).then(
      () => addToast("Link copied!", "success"),
      () => addToast("Failed to copy link", "error"),
    );
  };

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

  const postPreview = post
    ? {
        title: post.title,
        image_url: post.image_url,
        author_username: post.author_username,
        author_avatar_url: post.author_avatar_url,
        community_name: post.community_name,
      }
    : null;

  return (
    <Modal open={open} onClose={onClose} title="Share post">
      {/* Tab toggle */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tabBtn} ${tab === "send" ? styles.tabActive : ""}`}
          onClick={() => setTab("send")}
          type="button"
        >
          Send to
        </button>
        <button
          className={`${styles.tabBtn} ${tab === "reshare" ? styles.tabActive : ""}`}
          onClick={() => setTab("reshare")}
          type="button"
        >
          Reshare
        </button>
      </div>

      {tab === "send" && (
        <form className={styles.form} onSubmit={handleSendDM}>
          {/* Post preview card */}
          {postPreview && (
            <div className={styles.postCard}>
              {postPreview.image_url && (
                <img
                  className={styles.postCardImg}
                  src={postPreview.image_url}
                  alt=""
                />
              )}
              <div className={styles.postCardBody}>
                <span className={styles.postCardTitle}>{postPreview.title}</span>
                <span className={styles.postCardMeta}>
                  {postPreview.author_username && `@${postPreview.author_username}`}
                  {postPreview.community_name &&
                    ` in c/${postPreview.community_name}`}
                </span>
              </div>
            </div>
          )}

          {/* User search */}
          <label className={styles.label}>
            Send to
            <input
              className={styles.input}
              value={selectedUser ? `@${selectedUser.username}` : query}
              onChange={(e) => {
                setSelectedUser(null);
                setQuery(e.target.value);
              }}
              placeholder="Search for a user..."
              autoComplete="off"
            />
          </label>

          {/* Search results dropdown */}
          {results.length > 0 && !selectedUser && (
            <ul className={styles.userList}>
              {results.map((u) => (
                <li key={u.id}>
                  <button
                    className={styles.userItem}
                    type="button"
                    onClick={() => {
                      setSelectedUser(u);
                      setQuery("");
                      setResults([]);
                    }}
                  >
                    <Avatar
                      src={u.avatar_url}
                      alt={`@${u.username}`}
                      size={28}
                    />
                    <span>@{u.username}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* Optional message */}
          <textarea
            className={styles.comment}
            value={dmText}
            onChange={(e) => setDmText(e.target.value)}
            placeholder="Add a message (optional)"
            maxLength={2000}
            rows={2}
          />

          {/* Encryption badge */}
          <div className={styles.encBadge}>
            <span className={styles.encLock}>&#128274;</span>
            <span className={styles.encText}>End-to-end encrypted</span>
            <InfoTooltip>
              Messages are encrypted on your device using AES-256-GCM before
              being sent. The encryption key is wrapped with the recipient's
              RSA-OAEP public key so only they can read it. PimPam's servers
              never see the plaintext.
            </InfoTooltip>
          </div>

          {sendError && (
            <p className={styles.error} role="alert">
              {sendError}
            </p>
          )}

          <div className={styles.actions}>
            <button
              className={styles.copyBtn}
              type="button"
              onClick={handleCopyLink}
            >
              Copy link
            </button>
            <button
              className={styles.submitBtn}
              type="submit"
              disabled={sending || !selectedUser}
            >
              {sending ? <Spinner size={16} /> : "Send"}
            </button>
          </div>
        </form>
      )}

      {tab === "reshare" && (
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
            <button
              className={styles.copyBtn}
              type="button"
              onClick={handleCopyLink}
            >
              Copy link
            </button>
            <button
              className={styles.submitBtn}
              type="submit"
              disabled={sharing}
            >
              {sharing ? <Spinner size={16} /> : "Share"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
