import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "../api/stories";
import { upload } from "../api/media";
import { autocompleteUsers } from "../api/users";
import { getLinkPreview } from "../api/posts";
import { getCloseFriends } from "../api/friendGroups";
import { useToast } from "../contexts/ToastContext";
import Modal from "./ui/Modal";
import Button from "./ui/Button";
import ImageIcon from "./ui/icons/ImageIcon";
import Avatar from "./ui/Avatar";
import InfoTooltip from "./ui/InfoTooltip";
import styles from "./StoryCompose.module.css";

const DURATION_OPTIONS = [
  { label: "12h", value: 12 },
  { label: "24h", value: 24 },
  { label: "48h", value: 48 },
  { label: "7 days", value: 168 },
];

const STORY_TYPES = [
  { key: "image", label: "Image" },
  { key: "link", label: "Link" },
  { key: "both", label: "Image + Link" },
];

const VISIBILITY_OPTIONS = [
  { key: "close_friends", label: "Close Friends" },
  { key: "followers", label: "Followers" },
  { key: "public", label: "Public" },
];

const DEFAULT_STORY_VISIBILITY_KEY = "pimpam_default_story_visibility";

export default function StoryCompose({ open, onClose }) {
  const { addToast } = useToast();
  const fileRef = useRef(null);
  const mentionRef = useRef(null);

  const [storyType, setStoryType] = useState("image");
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkPreview, setLinkPreview] = useState(null);
  const [linkLoading, setLinkLoading] = useState(false);
  const [caption, setCaption] = useState("");
  const [duration, setDuration] = useState(24);
  const [visibility, setVisibility] = useState(
    () => localStorage.getItem(DEFAULT_STORY_VISIBILITY_KEY) || "close_friends"
  );
  const [closeFriendsCount, setCloseFriendsCount] = useState(null);
  const [loading, setLoading] = useState(false);

  // @mention autocomplete state
  const [mentionQuery, setMentionQuery] = useState(null);
  const [mentionResults, setMentionResults] = useState([]);
  const [mentionIndex, setMentionIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState(-1);

  const hasImage = storyType === "image" || storyType === "both";
  const hasLink = storyType === "link" || storyType === "both";

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const reset = () => {
    setStoryType("image");
    setPreview(null);
    setFile(null);
    setLinkUrl("");
    setLinkPreview(null);
    setCaption("");
    setDuration(24);
    setVisibility(localStorage.getItem(DEFAULT_STORY_VISIBILITY_KEY) || "close_friends");
    setMentionQuery(null);
    setMentionResults([]);
    if (fileRef.current) fileRef.current.value = "";
  };

  // Fetch close friends count when modal opens
  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const { data } = await getCloseFriends();
        setCloseFriendsCount(data.member_count);
      } catch {
        setCloseFriendsCount(0);
      }
    })();
  }, [open]);

  // Fetch link preview on blur or after debounce
  const fetchPreview = useCallback(async (url) => {
    if (!url) {
      setLinkPreview(null);
      return;
    }
    setLinkLoading(true);
    try {
      const { data } = await getLinkPreview(url);
      if (data.title || data.image) setLinkPreview(data);
      else setLinkPreview(null);
    } catch {
      setLinkPreview(null);
    } finally {
      setLinkLoading(false);
    }
  }, []);

  // Debounce link preview fetch
  useEffect(() => {
    if (!hasLink || !linkUrl) return;
    const t = setTimeout(() => fetchPreview(linkUrl), 800);
    return () => clearTimeout(t);
  }, [linkUrl, hasLink, fetchPreview]);

  // @mention autocomplete fetch
  useEffect(() => {
    if (mentionQuery === null || mentionQuery.length < 1) {
      setMentionResults([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await autocompleteUsers(mentionQuery);
        setMentionResults(data);
        setMentionIndex(0);
      } catch {
        setMentionResults([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [mentionQuery]);

  const handleCaptionChange = (e) => {
    const value = e.target.value;
    setCaption(value);

    const pos = e.target.selectionStart;
    const textBefore = value.slice(0, pos);
    const match = textBefore.match(/@([a-zA-Z0-9_]*)$/);
    if (match) {
      setMentionStart(pos - match[0].length);
      setMentionQuery(match[1]);
    } else {
      setMentionQuery(null);
      setMentionResults([]);
    }
  };

  const insertMention = (username) => {
    const before = caption.slice(0, mentionStart);
    const after = caption.slice(
      mentionStart + (mentionQuery ? mentionQuery.length + 1 : 1)
    );
    const newCaption = `${before}@${username} ${after}`;
    setCaption(newCaption);
    setMentionQuery(null);
    setMentionResults([]);
    // Focus the input after insertion
    setTimeout(() => mentionRef.current?.focus(), 0);
  };

  const handleCaptionKeyDown = (e) => {
    if (mentionResults.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setMentionIndex((i) => Math.min(i + 1, mentionResults.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setMentionIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (mentionResults[mentionIndex]) {
        insertMention(mentionResults[mentionIndex].username);
      }
    } else if (e.key === "Escape") {
      setMentionQuery(null);
      setMentionResults([]);
    }
  };

  const canSubmit =
    (hasImage ? !!file : true) && (hasLink ? !!linkUrl : true);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setLoading(true);
    try {
      const payload = { caption: caption || null, duration_hours: duration, visibility };
      if (file) {
        const { data: media } = await upload(file, "post_image");
        payload.image_url = media.url;
      }
      if (hasLink && linkUrl) {
        payload.link_url = linkUrl;
      }
      await create(payload);
      addToast("Story posted!", "success");
      reset();
      onClose();
    } catch {
      addToast("Failed to post story.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const showForm = storyType === "link" || preview;

  return (
    <Modal open={open} onClose={handleClose} title="New story">
      {/* Story type toggle */}
      <div className={styles.typeToggle}>
        {STORY_TYPES.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`${styles.typeBtn} ${storyType === t.key ? styles.typeActive : ""}`}
            onClick={() => setStoryType(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Image picker — shown if type needs image and none selected */}
      {hasImage && !preview && (
        <div className={styles.picker}>
          <button
            className={styles.pickBtn}
            onClick={() => fileRef.current?.click()}
            aria-label="Choose image"
          >
            <ImageIcon size={32} />
            <span>Choose an image</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleFile}
            hidden
          />
        </div>
      )}

      {/* Form shown once we have content (image preview or link-only mode) */}
      {showForm && (
        <div className={styles.form}>
          {preview && (
            <img src={preview} alt="Preview" className={styles.preview} />
          )}

          {/* Link URL input */}
          {hasLink && (
            <>
              <label htmlFor="story-link" className={styles.label}>
                Link URL
              </label>
              <input
                id="story-link"
                type="url"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                placeholder="https://..."
                className={styles.input}
              />
              {linkLoading && (
                <span className={styles.linkStatus}>Loading preview...</span>
              )}
              {linkPreview && !linkLoading && (
                <div className={styles.linkCard}>
                  {linkPreview.image && (
                    <img
                      src={linkPreview.image}
                      alt=""
                      className={styles.linkImage}
                      onError={(e) => { e.target.style.display = "none"; }}
                    />
                  )}
                  <div className={styles.linkBody}>
                    {linkPreview.title && (
                      <span className={styles.linkTitle}>{linkPreview.title}</span>
                    )}
                    {linkPreview.description && (
                      <span className={styles.linkDesc}>
                        {linkPreview.description}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Caption with @mention autocomplete */}
          <label htmlFor="story-caption" className={styles.label}>
            Caption (optional)
          </label>
          <div className={styles.captionWrap}>
            <input
              ref={mentionRef}
              id="story-caption"
              type="text"
              maxLength={200}
              value={caption}
              onChange={handleCaptionChange}
              onKeyDown={handleCaptionKeyDown}
              placeholder="Add a caption... use @ to tag people"
              className={styles.input}
              autoComplete="off"
              aria-expanded={mentionResults.length > 0}
              aria-haspopup="listbox"
              aria-controls="mention-list"
            />
            {mentionResults.length > 0 && (
              <ul
                id="mention-list"
                role="listbox"
                className={styles.mentionList}
              >
                {mentionResults.map((u, i) => (
                  <li
                    key={u.user_id}
                    role="option"
                    aria-selected={i === mentionIndex}
                    className={`${styles.mentionItem} ${i === mentionIndex ? styles.mentionActive : ""}`}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      insertMention(u.username);
                    }}
                  >
                    <Avatar username={u.username} avatarUrl={u.avatar_url} size={20} />
                    <span>@{u.username}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <span className={styles.charCount}>{caption.length}/200</span>

          <label className={styles.label}>Duration</label>
          <div className={styles.durations}>
            {DURATION_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.durBtn} ${duration === opt.value ? styles.durActive : ""}`}
                onClick={() => setDuration(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <label className={styles.label}>
            Who can see this
            <InfoTooltip>
              Close friends is your inner circle. Only the people you&apos;ve added
              to your close friends list will see this story. They won&apos;t know
              they&apos;re on the list. &quot;Followers&quot; means anyone who follows you.
              &quot;Public&quot; means everyone.
            </InfoTooltip>
          </label>
          <div className={styles.durations}>
            {VISIBILITY_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                type="button"
                className={`${styles.durBtn} ${visibility === opt.key ? styles.durActive : ""}`}
                onClick={() => {
                  setVisibility(opt.key);
                  localStorage.setItem(DEFAULT_STORY_VISIBILITY_KEY, opt.key);
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <span className={styles.visibilityInfo}>
            {visibility === "close_friends" && (
              closeFriendsCount != null
                ? closeFriendsCount > 0
                  ? `Sharing with ${closeFriendsCount} close friend${closeFriendsCount !== 1 ? "s" : ""}`
                  : "You haven't added anyone to close friends yet"
                : "Loading..."
            )}
            {visibility === "followers" && "Visible to everyone who follows you"}
            {visibility === "public" && "Visible to everyone"}
          </span>
          {visibility === "close_friends" && closeFriendsCount === 0 && (
            <a href="/friends" className={styles.manageLink}>Manage close friends →</a>
          )}

          <div className={styles.actions}>
            <Button variant="ghost" onClick={handleClose}>
              Cancel
            </Button>
            <Button loading={loading} onClick={handleSubmit} disabled={!canSubmit}>
              Post story
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
