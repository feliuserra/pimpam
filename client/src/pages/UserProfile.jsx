import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import PostCard from "../components/PostCard";
import UserCard from "../components/UserCard";
import EditProfileModal from "../components/EditProfileModal";
import SettingsIcon from "../components/ui/icons/SettingsIcon";
import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";
import styles from "./UserProfile.module.css";

const TABS = ["Posts", "Followers", "Following"];

export default function UserProfile() {
  const { username } = useParams();
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("Posts");
  const [following, setFollowing] = useState(null);
  const [followBusy, setFollowBusy] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  const isSelf = me && profile && me.id === profile.id;

  // Load profile
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setTab("Posts");
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
      // 409 = already following/not following — sync UI to server truth
      if (err?.response?.status === 409) {
        setFollowing(!following);
      }
    } finally {
      setFollowBusy(false);
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

      <div className={styles.container}>
        {/* Profile header */}
        <div className={styles.header}>
          <Avatar
            src={profile.avatar_url}
            alt={`@${profile.username}`}
            size={80}
          />
          <div className={styles.headerInfo}>
            <h1 className={styles.displayName}>
              {profile.display_name || `@${profile.username}`}
            </h1>
            <p className={styles.username}>@{profile.username}</p>
            {profile.bio && <p className={styles.bio}>{profile.bio}</p>}
          </div>
        </div>

        {/* Stats */}
        <div className={styles.stats}>
          <button
            className={styles.stat}
            onClick={() => setTab("Followers")}
          >
            <strong>{profile.follower_count}</strong> followers
          </button>
          <button
            className={styles.stat}
            onClick={() => setTab("Following")}
          >
            <strong>{profile.following_count}</strong> following
          </button>
          <span className={styles.stat}>
            <strong>{profile.karma}</strong> karma
          </span>
        </div>

        {/* Follow / Edit button */}
        {me && !isSelf && (
          <button
            className={`${styles.followBtn} ${following ? styles.following : ""}`}
            onClick={toggleFollow}
            disabled={followBusy}
          >
            {following ? "Following" : "Follow"}
          </button>
        )}
        {isSelf && (
          <button
            className={styles.editBtn}
            onClick={() => setEditOpen(true)}
          >
            Edit profile
          </button>
        )}

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
        {tab === "Posts" && <PostsTab username={profile.username} />}
        {tab === "Followers" && <UserListTab username={profile.username} type="followers" />}
        {tab === "Following" && <UserListTab username={profile.username} type="following" />}
      </div>

      <EditProfileModal
        open={editOpen}
        onClose={() => {
          setEditOpen(false);
          // Refresh profile after edit
          usersApi.getUser(username).then((res) => setProfile(res.data)).catch(() => {});
        }}
      />
    </>
  );
}

function PostsTab({ username }) {
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
          onDelete={(id) => setPosts((prev) => prev.filter((p) => p.id !== id))}
        />
      ))}
    </section>
  );
}

function UserListTab({ username, type }) {
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
        <UserCard key={u.id} user={u} />
      ))}
    </div>
  );
}
