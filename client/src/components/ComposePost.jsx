import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "../api/posts";
import { listJoined } from "../api/communities";
import { upload } from "../api/media";
import * as labelsApi from "../api/communityLabels";
import { getCloseFriends, list as listFriendGroups } from "../api/friendGroups";
import { useToast } from "../contexts/ToastContext";
import Modal from "./ui/Modal";
import Button from "./ui/Button";
import ImageIcon from "./ui/icons/ImageIcon";
import CloseIcon from "./ui/icons/CloseIcon";
import InfoTooltip from "./ui/InfoTooltip";
import styles from "./ComposePost.module.css";

const VISIBILITY_OPTIONS = [
  { key: "public", label: "Public" },
  { key: "followers", label: "Followers" },
  { key: "close_friends", label: "Close Friends" },
  { key: "group", label: "Group..." },
];

const DEFAULT_POST_VISIBILITY_KEY = "pimpam_default_post_visibility";

export default function ComposePost({ open, onClose, onCreated, defaultCommunityId }) {
  const { addToast } = useToast();
  const fileRef = useRef(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [communityId, setCommunityId] = useState(defaultCommunityId ? String(defaultCommunityId) : "");
  const [communities, setCommunities] = useState([]);
  const [labelId, setLabelId] = useState("");
  const [labels, setLabels] = useState([]);
  const [visibility, setVisibility] = useState(
    () => localStorage.getItem(DEFAULT_POST_VISIBILITY_KEY) || "public"
  );
  const [friendGroups, setFriendGroups] = useState([]);
  const [friendGroupId, setFriendGroupId] = useState(null);
  const [closeFriendsCount, setCloseFriendsCount] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchCommunities = useCallback(async () => {
    try {
      const { data } = await listJoined();
      setCommunities(data);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    if (open) {
      fetchCommunities();
      // Fetch close friends count + friend groups for visibility selector
      getCloseFriends()
        .then(({ data }) => setCloseFriendsCount(data.member_count))
        .catch(() => setCloseFriendsCount(0));
      listFriendGroups()
        .then(({ data }) => setFriendGroups(data.filter((g) => !g.is_close_friends)))
        .catch(() => setFriendGroups([]));
    }
  }, [open, fetchCommunities]);

  // Fetch labels when community changes
  useEffect(() => {
    if (!communityId) {
      setLabels([]);
      setLabelId("");
      return;
    }
    const comm = communities.find((c) => String(c.id) === communityId);
    if (comm) {
      labelsApi.list(comm.name).then((r) => setLabels(r.data)).catch(() => setLabels([]));
    }
    setLabelId("");
  }, [communityId, communities]);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImageFile(f);
    setImagePreview(URL.createObjectURL(f));
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const reset = () => {
    setTitle("");
    setContent("");
    setUrl("");
    setCommunityId(defaultCommunityId ? String(defaultCommunityId) : "");
    setLabelId("");
    setVisibility(localStorage.getItem(DEFAULT_POST_VISIBILITY_KEY) || "public");
    setFriendGroupId(null);
    removeImage();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    try {
      let image_url = null;
      if (imageFile) {
        const { data: media } = await upload(imageFile, "post_image");
        image_url = media.url;
      }
      const effectiveVisibility = communityId ? "public" : visibility;
      const body = {
        title: title.trim(),
        content: content.trim() || null,
        url: url.trim() || null,
        image_url,
        community_id: communityId ? Number(communityId) : null,
        label_id: labelId ? Number(labelId) : null,
        visibility: effectiveVisibility,
        friend_group_id: effectiveVisibility === "group" ? friendGroupId : null,
      };
      const { data: post } = await create(body);
      addToast("Post created!", "success");
      reset();
      onClose();
      onCreated?.(post);
    } catch (err) {
      const detail = err.response?.data?.detail;
      addToast(typeof detail === "string" ? detail : "Failed to create post.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="New post">
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Title *"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={styles.titleInput}
          required
        />

        <textarea
          placeholder="What's on your mind?"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className={styles.textarea}
          rows={4}
        />

        <input
          type="url"
          placeholder="Link (optional)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className={styles.input}
        />

        {communities.length > 0 && (
          <select
            value={communityId}
            onChange={(e) => setCommunityId(e.target.value)}
            className={styles.input}
            aria-label="Community"
          >
            <option value="">No community (personal)</option>
            {communities.map((c) => (
              <option key={c.id} value={c.id}>
                c/{c.name}
              </option>
            ))}
          </select>
        )}

        {labels.length > 0 && (
          <select
            value={labelId}
            onChange={(e) => setLabelId(e.target.value)}
            className={styles.input}
            aria-label="Label"
          >
            <option value="">No label</option>
            {labels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        )}

        {/* Visibility selector — hidden when posting to a community (always public) */}
        {!communityId ? (
          <div className={styles.visSection}>
            <label className={styles.visLabel}>
              Who can see this
              <InfoTooltip>
                Choose who can see this post. &quot;Public&quot; means everyone.
                &quot;Followers&quot; means people who follow you. &quot;Close Friends&quot;
                is your inner circle. &quot;Group&quot; lets you pick a specific friend group.
              </InfoTooltip>
            </label>
            <div className={styles.visToggle}>
              {VISIBILITY_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  className={`${styles.visBtn} ${visibility === opt.key ? styles.visBtnActive : ""}`}
                  onClick={() => {
                    setVisibility(opt.key);
                    if (opt.key !== "group") {
                      setFriendGroupId(null);
                      localStorage.setItem(DEFAULT_POST_VISIBILITY_KEY, opt.key);
                    }
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            {visibility === "group" && (
              <select
                value={friendGroupId || ""}
                onChange={(e) => setFriendGroupId(e.target.value ? Number(e.target.value) : null)}
                className={styles.input}
                aria-label="Friend group"
              >
                <option value="">Select a group...</option>
                {friendGroups.map((g) => (
                  <option key={g.id} value={g.id}>{g.name} ({g.member_count})</option>
                ))}
              </select>
            )}
            <span className={styles.visInfo}>
              {visibility === "public" && "Anyone can see this post"}
              {visibility === "followers" && "Only your followers will see this"}
              {visibility === "close_friends" && (
                closeFriendsCount != null
                  ? closeFriendsCount > 0
                    ? `Sharing with ${closeFriendsCount} close friend${closeFriendsCount !== 1 ? "s" : ""}`
                    : "You haven't added anyone to close friends yet"
                  : "Loading..."
              )}
              {visibility === "group" && friendGroupId && (() => {
                const g = friendGroups.find((fg) => fg.id === friendGroupId);
                return g ? `Only members of "${g.name}" will see this` : "";
              })()}
            </span>
          </div>
        ) : (
          <span className={styles.visInfo}>Community posts are always public</span>
        )}

        {imagePreview ? (
          <div className={styles.imageWrap}>
            <img src={imagePreview} alt="Upload preview" className={styles.imagePreview} />
            <button
              type="button"
              className={styles.removeImage}
              onClick={removeImage}
              aria-label="Remove image"
            >
              <CloseIcon size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            className={styles.addImage}
            onClick={() => fileRef.current?.click()}
          >
            <ImageIcon size={18} />
            <span>Add image</span>
          </button>
        )}

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleFile}
          hidden
        />

        <div className={styles.actions}>
          <Button variant="ghost" type="button" onClick={handleClose}>Cancel</Button>
          <Button type="submit" loading={loading} disabled={!title.trim()}>Post</Button>
        </div>
      </form>
    </Modal>
  );
}
