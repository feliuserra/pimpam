import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import Header from "../components/Header";
import Spinner from "../components/ui/Spinner";
import PostCard from "../components/PostCard";
import ComposePost from "../components/ComposePost";
import PlusIcon from "../components/ui/icons/PlusIcon";
import { useAuth } from "../contexts/AuthContext";
import { useInfiniteList } from "../hooks/useInfiniteList";
import * as communitiesApi from "../api/communities";
import styles from "./CommunityPage.module.css";

export default function CommunityPage() {
  const { name } = useParams();
  const { user } = useAuth();
  const [community, setCommunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [joined, setJoined] = useState(false);
  const [joinBusy, setJoinBusy] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);

  // Load community info
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
    return () => { cancelled = true; };
  }, [name]);

  // Check membership
  useEffect(() => {
    if (!user || !community) return;
    communitiesApi
      .listJoined()
      .then((res) => {
        setJoined(res.data.some((c) => c.id === community.id));
      })
      .catch(() => {});
  }, [user, community]);

  // Posts
  const fetchPosts = useCallback(
    (cursor) => communitiesApi.getPosts(name, { limit: 20, before_id: cursor }),
    [name],
  );
  const { items: posts, setItems: setPosts, loading: postsLoading, hasMore, sentinelRef, refresh } =
    useInfiniteList(fetchPosts);

  useEffect(() => { if (community) refresh(); }, [community, refresh]);

  const toggleJoin = async () => {
    if (joinBusy || !user) return;
    setJoinBusy(true);
    try {
      if (joined) {
        await communitiesApi.leave(name);
        setJoined(false);
        setCommunity((c) => c && { ...c, member_count: c.member_count - 1 });
      } else {
        await communitiesApi.join(name);
        setJoined(true);
        setCommunity((c) => c && { ...c, member_count: c.member_count + 1 });
      }
    } catch {
      // silent
    } finally {
      setJoinBusy(false);
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
          <h1 className={styles.name}>c/{community.name}</h1>
          {community.description && (
            <p className={styles.desc}>{community.description}</p>
          )}
          <span className={styles.members}>
            {community.member_count.toLocaleString()} members
          </span>
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
            {joined && (
              <Link to={`/c/${name}/mod`} className={styles.modLink}>
                Mod Panel
              </Link>
            )}
          </div>
        )}

        {/* Posts */}
        <section aria-label="Community posts">
          {posts.length === 0 && !postsLoading && (
            <p className={styles.empty}>No posts in this community yet.</p>
          )}
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
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
