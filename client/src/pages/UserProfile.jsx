import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import PostCard from "../components/PostCard";
import UserCard from "../components/UserCard";
import CropModal from "../components/CropModal";
import SettingsIcon from "../components/ui/icons/SettingsIcon";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import * as usersApi from "../api/users";
import * as postsApi from "../api/posts";
import * as mediaApi from "../api/media";
import styles from "./UserProfile.module.css";

const TABS = ["Posts", "Followers", "Following"];
const DEFAULT_LAYOUT = ["bio", "pinned_post", "community_stats"];

export default function UserProfile() {
  const { username } = useParams();
  const navigate = useNavigate();
  const { user: me, updateUser } = useAuth();
  const { addToast } = useToast();
  const { isCloseFriend } = useCloseFriends();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("Posts");
  const [following, setFollowing] = useState(null);
  const [followBusy, setFollowBusy] = useState(false);

  // Inline edit state
  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState({});
  const [saving, setSaving] = useState(false);
  const [coverUploading, setCoverUploading] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [cropSrc, setCropSrc] = useState(null); // object URL for crop modal
  const [cropType, setCropType] = useState(null); // "avatar" or "cover"

  // Pinned post
  const [pinnedPost, setPinnedPost] = useState(null);

  // Community stats
  const [communityStats, setCommunityStats] = useState(null);

  // Layout drag
  const [dragIdx, setDragIdx] = useState(null);

  const isSelf = me && profile && me.id === profile.id;

  // Load profile
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setTab("Posts");
    setEditMode(false);
    usersApi
      .getUser(username)
      .then((res) => {
        if (cancelled) return;
        setProfile(res.data);
        setFollowing(res.data.is_following);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("User not found");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [username]);

  // Load pinned post
  useEffect(() => {
    if (!profile?.pinned_post_id) { setPinnedPost(null); return; }
    postsApi.get(profile.pinned_post_id)
      .then((res) => setPinnedPost(res.data))
      .catch(() => setPinnedPost(null));
  }, [profile?.pinned_post_id]);

  // Load community stats
  useEffect(() => {
    if (!profile) return;
    usersApi.getCommunityStats(profile.username)
      .then((res) => setCommunityStats(res.data))
      .catch(() => setCommunityStats(null));
  }, [profile?.username, profile?.show_community_stats]);

  // Track S3 keys from uploads (separate from signed URLs used for display)
  const uploadedKeys = useRef({});

  // Enter edit mode
  const startEdit = () => {
    uploadedKeys.current = {};
    setDraft({
      display_name: profile.display_name || "",
      bio: profile.bio || "",
      avatar_url: profile.avatar_url || "",
      cover_image_url: profile.cover_image_url || "",
      accent_color: profile.accent_color || "",
      location: profile.location || "",
      website: profile.website || "",
      pronouns: profile.pronouns || "",
      profile_layout: profile.profile_layout || DEFAULT_LAYOUT,
      show_community_stats: profile.show_community_stats !== false,
      show_posts_on_profile: profile.show_posts_on_profile !== false,
      cover_gradient: profile.cover_gradient !== false,
    });
    setEditMode(true);
  };

  // Save edits
  const saveEdit = async () => {
    if (saving) return;
    setSaving(true);
    try {
      const payload = {};
      if (draft.display_name !== (profile.display_name || "")) payload.display_name = draft.display_name || null;
      if (draft.bio !== (profile.bio || "")) payload.bio = draft.bio || null;
      if (draft.avatar_url !== (profile.avatar_url || "")) payload.avatar_url = uploadedKeys.current.avatar_url || draft.avatar_url || null;
      if (draft.cover_image_url !== (profile.cover_image_url || "")) payload.cover_image_url = uploadedKeys.current.cover_image_url || draft.cover_image_url || "";
      if (draft.accent_color !== (profile.accent_color || "")) payload.accent_color = draft.accent_color || "";
      if (draft.location !== (profile.location || "")) payload.location = draft.location || null;
      if (draft.website !== (profile.website || "")) payload.website = draft.website || "";
      if (draft.pronouns !== (profile.pronouns || "")) payload.pronouns = draft.pronouns || null;
      if (JSON.stringify(draft.profile_layout) !== JSON.stringify(profile.profile_layout || DEFAULT_LAYOUT)) {
        payload.profile_layout = draft.profile_layout;
      }
      if (draft.show_community_stats !== (profile.show_community_stats !== false)) {
        payload.show_community_stats = draft.show_community_stats;
      }
      if (draft.cover_gradient !== (profile.cover_gradient !== false)) {
        payload.cover_gradient = draft.cover_gradient;
      }

      if (Object.keys(payload).length > 0) {
        const res = await usersApi.updateMe(payload);
        setProfile(res.data);
        updateUser(res.data);
      }
      setEditMode(false);
      addToast("Profile updated", "success");
    } catch {
      addToast("Failed to save profile", "error");
    } finally {
      setSaving(false);
    }
  };

  const cancelEdit = () => {
    setEditMode(false);
    setDraft({});
  };

  // File selection — opens crop modal (or uploads GIF directly)
  const handleFileSelect = async (e, type) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = ""; // reset so same file can be re-selected

    // GIF covers bypass crop modal to preserve animation
    if (type === "cover" && file.type === "image/gif") {
      setCoverUploading(true);
      try {
        const res = await mediaApi.upload(file, "cover_image");
        uploadedKeys.current.cover_image_url = res.data.key;
        setDraft((d) => ({ ...d, cover_image_url: res.data.url }));
      } catch {
        addToast("Failed to upload cover image", "error");
      } finally {
        setCoverUploading(false);
      }
      return;
    }

    const url = URL.createObjectURL(file);
    setCropSrc(url);
    setCropType(type);
  };

  // Crop confirmed — upload the cropped blob
  const handleCropConfirm = async (blob) => {
    const type = cropType;
    setCropSrc(null);
    setCropType(null);

    const file = new File([blob], `${type}.webp`, { type: "image/webp" });
    const mediaType = type === "cover" ? "cover_image" : "avatar";
    const setUploading = type === "cover" ? setCoverUploading : setAvatarUploading;
    const draftKey = type === "cover" ? "cover_image_url" : "avatar_url";

    setUploading(true);
    try {
      const res = await mediaApi.upload(file, mediaType);
      uploadedKeys.current[draftKey] = res.data.key;
      setDraft((d) => ({ ...d, [draftKey]: res.data.url }));
    } catch {
      addToast(`Failed to upload ${type === "cover" ? "cover image" : "avatar"}`, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleCropCancel = () => {
    if (cropSrc) URL.revokeObjectURL(cropSrc);
    setCropSrc(null);
    setCropType(null);
  };

  // Drag and drop for layout sections
  const handleDragStart = (idx) => setDragIdx(idx);
  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (targetIdx) => {
    if (dragIdx === null || dragIdx === targetIdx) return;
    setDraft((d) => {
      const layout = [...d.profile_layout];
      const [item] = layout.splice(dragIdx, 1);
      layout.splice(targetIdx, 0, item);
      return { ...d, profile_layout: layout };
    });
    setDragIdx(null);
  };

  // Follow/unfollow
  const toggleFollow = async () => {
    if (followBusy || !profile) return;
    setFollowBusy(true);
    try {
      if (following) {
        await usersApi.unfollow(profile.username);
        setFollowing(false);
        setProfile((p) => ({ ...p, follower_count: p.follower_count - 1 }));
      } else {
        await usersApi.follow(profile.username);
        setFollowing(true);
        setProfile((p) => ({ ...p, follower_count: p.follower_count + 1 }));
      }
    } catch (err) {
      if (err?.response?.status === 409) setFollowing(!following);
    } finally {
      setFollowBusy(false);
    }
  };

  // Pin/unpin
  const handlePin = async (postId) => {
    try {
      await usersApi.pinPost(postId);
      setProfile((p) => ({ ...p, pinned_post_id: postId }));
      addToast("Post pinned to your profile", "success");
    } catch {
      addToast("Failed to pin post", "error");
    }
  };

  const handleUnpin = async () => {
    try {
      await usersApi.unpinPost();
      setProfile((p) => ({ ...p, pinned_post_id: null }));
      setPinnedPost(null);
      addToast("Post unpinned", "success");
    } catch {
      addToast("Failed to unpin post", "error");
    }
  };

  if (loading) {
    return (
      <>
        <Header left={<span>@{username}</span>} />
        <div className={styles.loader}><Spinner size={28} /></div>
      </>
    );
  }

  if (error || !profile) {
    return (
      <>
        <Header left={<span>@{username}</span>} />
        <div className={styles.error}>{error || "User not found"}</div>
      </>
    );
  }

  const accentStyle = profile.accent_color
    ? { "--accent": profile.accent_color, "--color-accent": profile.accent_color }
    : {};

  const layout = profile.profile_layout || DEFAULT_LAYOUT;
  const editLayout = draft.profile_layout || DEFAULT_LAYOUT;

  const SECTION_LABELS = { bio: "Bio", pinned_post: "Pinned Post", community_stats: "Community Stats" };

  // Render a layout section
  const renderSection = (key) => {
    switch (key) {
      case "bio":
        return (
          <div key="bio" className={styles.section}>
            {profile.bio && <p className={styles.bio}>{profile.bio}</p>}
            <BioFields profile={profile} />
          </div>
        );
      case "pinned_post":
        if (!pinnedPost) return null;
        return (
          <div key="pinned_post" className={styles.section}>
            <div className={styles.pinnedLabel}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="17" x2="12" y2="22" />
                <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
              </svg>
              Pinned
              {isSelf && !editMode && (
                <button className={styles.unpinBtn} onClick={handleUnpin}>Unpin</button>
              )}
            </div>
            <PostCard post={pinnedPost} isCloseFriend={isCloseFriend(pinnedPost.author_id)} />
          </div>
        );
      case "community_stats":
        if (!communityStats) return null;
        if (!profile.show_community_stats && !isSelf) return null;
        return (
          <div key="community_stats" className={styles.section}>
            <h3 className={styles.sectionTitle}>Communities</h3>
            <div className={styles.communityStats}>
              <span><strong>{communityStats.joined}</strong> joined</span>
              <span className={styles.statDot}>·</span>
              <span><strong>{communityStats.moderating}</strong> moderating</span>
              <span className={styles.statDot}>·</span>
              <span><strong>{communityStats.owned}</strong> owned</span>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  // Render section in edit mode with drag handles
  const renderEditSection = (key, idx) => (
    <div
      key={key}
      className={styles.dragItem}
      draggable
      onDragStart={() => handleDragStart(idx)}
      onDragOver={handleDragOver}
      onDrop={() => handleDrop(idx)}
    >
      <span className={styles.dragHandle} aria-hidden="true">⠿</span>
      <span className={styles.dragLabel}>{SECTION_LABELS[key]}</span>
    </div>
  );

  const coverUrl = editMode ? draft.cover_image_url : profile.cover_image_url;
  const showGradient = editMode
    ? (draft.cover_gradient ?? true)
    : (profile.cover_gradient !== false);

  return (
    <>
      <Header
        left={<span>@{profile.username}</span>}
        right={
          isSelf ? (
            <button
              className={styles.iconBtn}
              onClick={() => navigate("/settings")}
              aria-label="Settings"
            >
              <SettingsIcon size={20} />
            </button>
          ) : null
        }
      />

      <div className={styles.profilePage} style={accentStyle}>
        {/* Full-bleed cover */}
        <div className={styles.coverWrap}>
          <div
            className={styles.cover}
            style={coverUrl ? { backgroundImage: `url(${coverUrl})` } : {}}
          >
            {/* Gradient overlay (view mode only, when enabled) */}
            {!editMode && coverUrl && showGradient && (
              <div className={styles.coverGradient} />
            )}

            {/* Display name overlaid on cover (view mode + has cover image) */}
            {!editMode && coverUrl && (
              <div className={styles.coverNameOverlay}>
                <h1 className={styles.coverDisplayName}>
                  {profile.display_name || `@${profile.username}`}
                </h1>
                <p className={styles.coverUsername}>@{profile.username}</p>
              </div>
            )}

            {editMode && (
              <label className={styles.coverOverlay}>
                {coverUploading ? "Uploading..." : "Change cover"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  onChange={(e) => handleFileSelect(e, "cover")}
                  className={styles.fileInput}
                  disabled={coverUploading}
                />
              </label>
            )}
          </div>
        </div>

        {/* Content container (600px max-width) */}
        <div className={styles.container}>
          {/* Profile header */}
          <div className={styles.header}>
            <div className={styles.avatarWrap}>
              <Avatar
                src={editMode ? draft.avatar_url : profile.avatar_url}
                alt={`@${profile.username}`}
                size={96}
                className={styles.profileAvatar}
              />
              {editMode && (
                <label className={styles.avatarOverlay}>
                  {avatarUploading ? "..." : "Edit"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => handleFileSelect(e, "avatar")}
                    className={styles.fileInput}
                    disabled={avatarUploading}
                  />
                </label>
              )}
            </div>
            <div className={styles.headerInfo}>
              {editMode ? (
                <input
                  className={styles.editInput}
                  value={draft.display_name}
                  onChange={(e) => setDraft((d) => ({ ...d, display_name: e.target.value }))}
                  maxLength={100}
                  placeholder="Display name"
                />
              ) : !coverUrl ? (
                <h1 className={styles.displayName}>
                  {profile.display_name || `@${profile.username}`}
                </h1>
              ) : null}
              <p className={styles.username}>
                {/* Show @username in headerInfo when name is on cover */}
                {!editMode && coverUrl ? (
                  <>
                    {profile.display_name || `@${profile.username}`}
                    {profile.pronouns && (
                      <span className={styles.pronouns}> ({profile.pronouns})</span>
                    )}
                  </>
                ) : (
                  <>
                    @{profile.username}
                    {!editMode && profile.pronouns && (
                      <span className={styles.pronouns}> ({profile.pronouns})</span>
                    )}
                  </>
                )}
              </p>
              {editMode && (
                <input
                  className={styles.editInput}
                  value={draft.pronouns}
                  onChange={(e) => setDraft((d) => ({ ...d, pronouns: e.target.value }))}
                  maxLength={50}
                  placeholder="she/her"
                />
              )}
            </div>
          </div>

          {/* Stats */}
          <div className={styles.stats}>
            <button className={styles.stat} onClick={() => setTab("Followers")}>
              <strong>{profile.follower_count}</strong> followers
            </button>
            <button className={styles.stat} onClick={() => setTab("Following")}>
              <strong>{profile.following_count}</strong> following
            </button>
            <span className={styles.stat}>
              <strong>{profile.karma}</strong> karma
            </span>
          </div>

          {/* Follow / Edit / Save-Cancel buttons */}
          {me && !isSelf && (
            <button
              className={`${styles.followBtn} ${following ? styles.following : ""}`}
              onClick={toggleFollow}
              disabled={followBusy}
            >
              {following ? "Following" : "Follow"}
            </button>
          )}
          {isSelf && !editMode && (
            <button className={styles.editBtn} onClick={startEdit}>
              Edit profile
            </button>
          )}
          {isSelf && editMode && (
            <div className={styles.editActions}>
              <button className={styles.cancelBtn} onClick={cancelEdit} disabled={saving}>
                Cancel
              </button>
              <button className={styles.saveBtn} onClick={saveEdit} disabled={saving || coverUploading || avatarUploading}>
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          )}

          {/* Edit mode: bio, extra fields, accent color, layout */}
          {editMode && (
            <div className={styles.editSection}>
              <label className={styles.editLabel}>
                Bio
                <textarea
                  className={styles.editTextarea}
                  value={draft.bio}
                  onChange={(e) => setDraft((d) => ({ ...d, bio: e.target.value }))}
                  maxLength={500}
                  placeholder="Tell people about yourself"
                  rows={3}
                />
              </label>
              <label className={styles.editLabel}>
                Location
                <input
                  className={styles.editInput}
                  value={draft.location}
                  onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
                  maxLength={100}
                  placeholder="Where are you based?"
                />
              </label>
              <label className={styles.editLabel}>
                Website
                <input
                  className={styles.editInput}
                  value={draft.website}
                  onChange={(e) => setDraft((d) => ({ ...d, website: e.target.value }))}
                  maxLength={500}
                  placeholder="https://..."
                />
              </label>
              <div className={styles.editLabel}>
                Accent color
                <div className={styles.colorRow}>
                  <input
                    type="color"
                    value={draft.accent_color || "#6366f1"}
                    onChange={(e) => setDraft((d) => ({ ...d, accent_color: e.target.value }))}
                    className={styles.colorPicker}
                  />
                  <span className={styles.colorHex}>{draft.accent_color || "default"}</span>
                  {draft.accent_color && (
                    <button
                      type="button"
                      className={styles.resetLink}
                      onClick={() => setDraft((d) => ({ ...d, accent_color: "" }))}
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>
              <label className={styles.editLabel}>
                <span className={styles.toggleRow}>
                  Cover gradient
                  <input
                    type="checkbox"
                    checked={draft.cover_gradient}
                    onChange={(e) => setDraft((d) => ({ ...d, cover_gradient: e.target.checked }))}
                  />
                </span>
              </label>
              <label className={styles.editLabel}>
                <span className={styles.toggleRow}>
                  Show community stats
                  <input
                    type="checkbox"
                    checked={draft.show_community_stats}
                    onChange={(e) => setDraft((d) => ({ ...d, show_community_stats: e.target.checked }))}
                  />
                </span>
              </label>
              <label className={styles.editLabel}>
                <span className={styles.toggleRow}>
                  Show posts on profile
                  <input
                    type="checkbox"
                    checked={draft.show_posts_on_profile ?? true}
                    onChange={(e) => setDraft((d) => ({ ...d, show_posts_on_profile: e.target.checked }))}
                  />
                </span>
              </label>
              <div className={styles.editLabel}>
                Layout order
                <p className={styles.editHint}>Drag to reorder profile sections</p>
                <div className={styles.dragList}>
                  {editLayout.map((key, idx) => renderEditSection(key, idx))}
                </div>
              </div>
            </div>
          )}

          {/* Profile sections (view mode) */}
          {!editMode && layout.map(renderSection)}

          {/* Tabs */}
          <nav className={styles.tabs} aria-label="Profile tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={`${styles.tab} ${tab === t ? styles.activeTab : ""}`}
                onClick={() => setTab(t)}
                aria-selected={tab === t}
                role="tab"
              >
                {t}
              </button>
            ))}
          </nav>

          {/* Tab content */}
          {tab === "Posts" && (
            !isSelf && profile.show_posts_on_profile === false ? (
              <p className={styles.empty}>This user has hidden their posts.</p>
            ) : (
              <PostsTab
                username={profile.username}
                isSelf={isSelf}
                pinnedPostId={profile.pinned_post_id}
                onPin={handlePin}
                onUnpin={handleUnpin}
                isCloseFriend={isCloseFriend}
              />
            )
          )}
          {tab === "Followers" && <UserListTab username={profile.username} type="followers" isCloseFriend={isCloseFriend} />}
          {tab === "Following" && <UserListTab username={profile.username} type="following" isCloseFriend={isCloseFriend} />}
        </div>
      </div>

      {/* Crop modal */}
      {cropSrc && (
        <CropModal
          src={cropSrc}
          aspect={cropType === "cover" ? 3 : 1}
          shape={cropType === "cover" ? "rect" : "circle"}
          onConfirm={handleCropConfirm}
          onCancel={handleCropCancel}
        />
      )}
    </>
  );
}

function BioFields({ profile }) {
  const hasFields = profile.location || profile.website;
  if (!hasFields) return null;

  return (
    <div className={styles.bioFields}>
      {profile.location && (
        <span className={styles.bioField}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          {profile.location}
        </span>
      )}
      {profile.website && (
        <a
          className={styles.bioField}
          href={profile.website}
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          {profile.website.replace(/^https?:\/\//, "")}
        </a>
      )}
    </div>
  );
}

function PostsTab({ username, isSelf, pinnedPostId, onPin, onUnpin, isCloseFriend }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    usersApi
      .getUserPosts(username, { limit: 50 })
      .then((res) => { if (!cancelled) setPosts(res.data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [username]);

  if (loading) {
    return <div className={styles.tabLoader}><Spinner size={20} /></div>;
  }

  if (posts.length === 0) {
    return <p className={styles.empty}>No posts yet.</p>;
  }

  return (
    <section>
      {posts.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          isCloseFriend={isCloseFriend(post.author_id)}
          onDelete={(id) => setPosts((prev) => prev.filter((p) => p.id !== id))}
          showPinAction={isSelf}
          isPinned={post.id === pinnedPostId}
          onPin={() => onPin(post.id)}
          onUnpin={onUnpin}
        />
      ))}
    </section>
  );
}

function UserListTab({ username, type, isCloseFriend }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const fetcher = type === "followers" ? usersApi.getFollowers : usersApi.getFollowing;
    fetcher(username, { limit: 50 })
      .then((res) => { if (!cancelled) setUsers(res.data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [username, type]);

  if (loading) {
    return <div className={styles.tabLoader}><Spinner size={20} /></div>;
  }

  if (users.length === 0) {
    return <p className={styles.empty}>No users.</p>;
  }

  return (
    <div>
      {users.map((u) => (
        <UserCard key={u.id} user={u} isCloseFriend={isCloseFriend(u.id)} />
      ))}
    </div>
  );
}
