import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import RelativeTime from "../components/ui/RelativeTime";
import PostCard from "../components/PostCard";
import ComposePost from "../components/ComposePost";
import PlusIcon from "../components/ui/icons/PlusIcon";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import { useInfiniteList } from "../hooks/useInfiniteList";
import * as communitiesApi from "../api/communities";
import * as labelsApi from "../api/communityLabels";
import * as mediaApi from "../api/media";
import styles from "./CommunityPage.module.css";

const ROLE_LABELS = {
  owner: "Owner",
  senior_mod: "Sr. Moderator",
  moderator: "Moderator",
  trusted_member: "Trusted Member",
  member: "Member",
};

const MOD_ROLES = new Set(["moderator", "senior_mod", "owner"]);

export default function CommunityPage() {
  const { name } = useParams();
  const { user } = useAuth();
  const { addToast } = useToast();
  const { isCloseFriend } = useCloseFriends();
  const avatarInputRef = useRef(null);
  const [community, setCommunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [joinBusy, setJoinBusy] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [showAudit, setShowAudit] = useState(false);
  const [labels, setLabels] = useState([]);
  const [activeLabel, setActiveLabel] = useState(null);

  // Load community info (includes user_role when authenticated)
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    communitiesApi
      .get(name)
      .then((res) => {
        if (cancelled) return;
        setCommunity(res.data);
        setError(null);
      })
      .catch(() => {
        if (!cancelled) setError("Community not found");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    labelsApi.list(name).then((r) => { if (!cancelled) setLabels(r.data); }).catch(() => {});
    return () => { cancelled = true; };
  }, [name, user]);

  // Posts
  const fetchPosts = useCallback(
    (cursor) => communitiesApi.getPosts(name, { limit: 20, before_id: cursor }),
    [name],
  );
  const { items: posts, setItems: setPosts, loading: postsLoading, hasMore, sentinelRef, refresh } =
    useInfiniteList(fetchPosts);

  useEffect(() => { if (community) refresh(); }, [community, refresh]);

  // Load audit log when toggled open
  useEffect(() => {
    if (!showAudit || !community) return;
    communitiesApi
      .getAuditLog(name, { limit: 50 })
      .then((res) => setAuditLog(res.data))
      .catch(() => {});
  }, [showAudit, community, name]);

  const userRole = community?.user_role;
  const joined = !!userRole;
  const isMod = MOD_ROLES.has(userRole);
  const canEditAvatar = isMod || getattr(user, "is_admin");

  const toggleJoin = async () => {
    if (joinBusy || !user) return;
    setJoinBusy(true);
    try {
      if (joined) {
        await communitiesApi.leave(name);
        setCommunity((c) => c && { ...c, user_role: null, member_count: c.member_count - 1 });
      } else {
        await communitiesApi.join(name);
        setCommunity((c) => c && { ...c, user_role: "member", member_count: c.member_count + 1 });
      }
    } catch {
      // silent
    } finally {
      setJoinBusy(false);
    }
  };

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingAvatar(true);
    try {
      const uploadRes = await mediaApi.upload(file, "avatar");
      const url = uploadRes.data.url;
      await communitiesApi.update(name, { avatar_url: url });
      setCommunity((c) => c && { ...c, avatar_url: url });
      addToast("Community avatar updated", "success");
    } catch {
      addToast("Failed to upload avatar", "error");
    } finally {
      setUploadingAvatar(false);
      if (avatarInputRef.current) avatarInputRef.current.value = "";
    }
  };

  if (loading) {
    return (
      <>
        <Header left={<span>c/{name}</span>} />
        <div className={styles.loader}><Spinner size={28} /></div>
      </>
    );
  }

  if (error || !community) {
    return (
      <>
        <Header left={<span>c/{name}</span>} />
        <div className={styles.error}>{error || "Community not found"}</div>
      </>
    );
  }

  return (
    <>
      <Header
        left={<span>c/{community.name}</span>}
        right={
          user && joined ? (
            <button
              className={styles.iconBtn}
              onClick={() => setComposeOpen(true)}
              aria-label="New post"
            >
              <PlusIcon size={20} />
            </button>
          ) : null
        }
      />

      <div className={styles.container}>
        {/* Community header */}
        <div className={styles.header}>
          <div className={styles.headerTop}>
            <div className={styles.avatarWrap}>
              <Avatar
                src={community.avatar_url}
                alt={community.name}
                size={64}
              />
              {canEditAvatar && (
                <label
                  className={styles.avatarOverlay}
                  aria-label="Change community avatar"
                >
                  {uploadingAvatar ? (
                    <Spinner size={16} />
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
                      <circle cx="12" cy="13" r="4"/>
                    </svg>
                  )}
                  <input
                    ref={avatarInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleAvatarUpload}
                    hidden
                    disabled={uploadingAvatar}
                  />
                </label>
              )}
            </div>
            <div className={styles.headerInfo}>
              <h1 className={styles.name}>c/{community.name}</h1>
              <span className={styles.members}>
                {community.member_count.toLocaleString()} members
              </span>
              {userRole && (
                <span className={`${styles.userRole} ${styles[`role_${userRole}`] || ""}`}>
                  {ROLE_LABELS[userRole] || userRole}
                </span>
              )}
            </div>
          </div>
          {community.description && (
            <p className={styles.desc}>{community.description}</p>
          )}
        </div>

        {/* Join/Leave + Mod link */}
        {user && (
          <div className={styles.actionRow}>
            <button
              className={`${styles.joinBtn} ${joined ? styles.joined : ""}`}
              onClick={toggleJoin}
              disabled={joinBusy}
            >
              {joined ? "Joined" : "Join"}
            </button>
            {isMod && (
              <Link to={`/c/${name}/mod`} className={styles.modLink}>
                Mod Panel
              </Link>
            )}
          </div>
        )}

        {/* Audit log toggle */}
        <button
          className={styles.auditToggle}
          onClick={() => setShowAudit((v) => !v)}
        >
          {showAudit ? "Hide activity log" : "Activity log"}
        </button>
        {showAudit && (
          <div className={styles.auditLog}>
            {auditLog.length === 0 ? (
              <p className={styles.auditEmpty}>No activity recorded yet.</p>
            ) : (
              auditLog.map((entry) => (
                <div key={entry.id} className={styles.auditEntry}>
                  <span className={styles.auditUser}>@{entry.actor_username}</span>
                  <span className={styles.auditAction}>{entry.detail || entry.action}</span>
                  <RelativeTime date={entry.created_at} className={styles.auditTime} />
                </div>
              ))
            )}
          </div>
        )}

        {/* Label filters */}
        {labels.length > 0 && (
          <div className={styles.labelFilters}>
            <button
              className={`${styles.labelPill} ${activeLabel === null ? styles.labelActive : ""}`}
              onClick={() => setActiveLabel(null)}
            >
              All
            </button>
            {labels.map((l) => (
              <button
                key={l.id}
                className={`${styles.labelPill} ${activeLabel === l.id ? styles.labelActive : ""}`}
                onClick={() => setActiveLabel(activeLabel === l.id ? null : l.id)}
                style={l.color ? { "--lbl-color": l.color } : undefined}
              >
                {l.color && <span className={styles.labelDot} style={{ background: l.color }} />}
                {l.name}
              </button>
            ))}
          </div>
        )}

        {/* Posts */}
        <section aria-label="Community posts">
          {posts.length === 0 && !postsLoading && (
            <p className={styles.empty}>No posts in this community yet.</p>
          )}
          {(activeLabel ? posts.filter((p) => p.label_id === activeLabel) : posts).map((post) => (
            <PostCard
              key={post.id}
              post={post}
              isCloseFriend={isCloseFriend(post.author_id)}
              onDelete={(id) => setPosts((prev) => prev.filter((p) => p.id !== id))}
            />
          ))}
          {hasMore && (
            <div ref={sentinelRef} className={styles.sentinel}>
              {postsLoading && <Spinner size={20} />}
            </div>
          )}
        </section>
      </div>

      <ComposePost
        open={composeOpen}
        onClose={() => setComposeOpen(false)}
        defaultCommunityId={community.id}
        onCreated={(post) => setPosts((prev) => [post, ...prev])}
      />
    </>
  );
}

function getattr(obj, key) {
  return obj ? obj[key] : false;
}
