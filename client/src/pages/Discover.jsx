import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import Spinner from "../components/ui/Spinner";
import PostCardSkeleton from "../components/PostCardSkeleton";
import { useAuth } from "../contexts/AuthContext";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import * as feedApi from "../api/feed";
import styles from "./Discover.module.css";

export default function Discover() {
  const { user } = useAuth();
  const defaultTab = "Trending";
  const tabs = user ? ["Trending", "For You", "News"] : ["Trending", "News"];
  const [tab, setTab] = useState(defaultTab);

  return (
    <>
      <Header left={<span>Discover</span>} />
      <div className={styles.container}>
        <nav className={styles.tabs} aria-label="Discover tabs">
          {tabs.map((t) => (
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

        {tab === "For You" && <ForYouList />}
        {tab === "Trending" && <TrendingList />}
        {tab === "News" && <NewsList />}
      </div>
    </>
  );
}

function ForYouList() {
  const { isCloseFriend } = useCloseFriends();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef(null);

  const load = useCallback(async (beforeId) => {
    try {
      const res = await feedApi.getForYou({
        limit: 20,
        ...(beforeId ? { before_id: beforeId } : {}),
      });
      const newPosts = res.data;
      if (newPosts.length < 20) setHasMore(false);
      setPosts((prev) => beforeId ? [...prev, ...newPosts] : newPosts);
    } catch {
      // silent
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Infinite scroll
  useEffect(() => {
    if (!hasMore || loading) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !loadingMore && posts.length > 0) {
          setLoadingMore(true);
          load(posts[posts.length - 1].id);
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loading, loadingMore, posts, load]);

  const handlePostUpdate = (updated) => {
    setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const handlePostDelete = (id) => {
    setPosts((prev) => prev.filter((p) => p.id !== id));
  };

  if (loading) return <div>{[1,2,3].map((i) => <PostCardSkeleton key={i} />)}</div>;

  if (posts.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p className={styles.emptyTitle}>Your For You feed is empty</p>
        <p className={styles.emptyText}>
          Follow hashtags or join communities to see personalized content here.
        </p>
        <div className={styles.emptyLinks}>
          <Link to="/communities" className={styles.emptyLink}>Browse communities</Link>
          <Link to="/search" className={styles.emptyLink}>Search hashtags</Link>
        </div>
        <p className={styles.emptyFormula}>
          Formula: posts matching your subscribed hashtags or picked by moderators in your communities, newest first. No algorithms.
        </p>
      </div>
    );
  }

  return (
    <div>
      <p className={styles.hint}>
        Posts from hashtags you follow and community picks. Chronological, transparent.
      </p>
      <div className={styles.list}>
        {posts.map((post) => (
          <PostCard
            key={post.id}
            post={post}
            isCloseFriend={isCloseFriend(post.author_id)}
            onUpdate={handlePostUpdate}
            onDelete={handlePostDelete}
          />
        ))}
        {hasMore && <div ref={sentinelRef} className={styles.loader}><Spinner size={16} /></div>}
      </div>
    </div>
  );
}

function TrendingList() {
  const { isCloseFriend } = useCloseFriends();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [window, setWindow] = useState(24);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await feedApi.getTrending({ limit: 15, hours: window });
      setPosts(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [window]);

  useEffect(() => { load(); }, [load]);

  const handlePostUpdate = (updated) => {
    setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const handlePostDelete = (id) => {
    setPosts((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <div>
      <div className={styles.windowPicker}>
        <span className={styles.windowLabel}>Time window:</span>
        {[24, 48, 168].map((h) => (
          <button
            key={h}
            className={`${styles.windowBtn} ${window === h ? styles.windowActive : ""}`}
            onClick={() => setWindow(h)}
          >
            {h === 168 ? "7d" : `${h}h`}
          </button>
        ))}
      </div>
      <p className={styles.hint}>
        Ranked by karma + comments. Non-personalised, transparent.
      </p>

      {loading ? (
        <div>{[1,2,3].map((i) => <PostCardSkeleton key={i} />)}</div>
      ) : posts.length === 0 ? (
        <p className={styles.empty}>No trending posts in this time window.</p>
      ) : (
        <div className={styles.list}>
          {posts.map((post, i) => (
            <div key={post.id} className={styles.ranked}>
              <span className={styles.rank}>#{i + 1}</span>
              <div className={styles.postWrap}>
                <PostCard
                  post={post}
                  isCloseFriend={isCloseFriend(post.author_id)}
                  onUpdate={handlePostUpdate}
                  onDelete={handlePostDelete}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NewsList() {
  const { isCloseFriend } = useCloseFriends();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef(null);

  const load = useCallback(async (beforeId) => {
    try {
      const res = await feedApi.getNews({
        limit: 20,
        ...(beforeId ? { before_id: beforeId } : {}),
      });
      const newPosts = res.data;
      if (newPosts.length < 20) setHasMore(false);
      setPosts((prev) => beforeId ? [...prev, ...newPosts] : newPosts);
    } catch {
      // silent
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Infinite scroll
  useEffect(() => {
    if (!hasMore || loading) return;
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !loadingMore && posts.length > 0) {
          setLoadingMore(true);
          load(posts[posts.length - 1].id);
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loading, loadingMore, posts, load]);

  const handlePostUpdate = (updated) => {
    setPosts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const handlePostDelete = (id) => {
    setPosts((prev) => prev.filter((p) => p.id !== id));
  };

  if (loading) return <div>{[1,2,3].map((i) => <PostCardSkeleton key={i} />)}</div>;
  if (posts.length === 0) return <p className={styles.empty}>No news posts yet.</p>;

  return (
    <div>
      <p className={styles.hint}>
        Posts from communities with &ldquo;news&rdquo; or &ldquo;noticias&rdquo; in their name, or tagged #news. Chronological, no editorial filter.
      </p>
      <div className={styles.list}>
        {posts.map((post) => (
          <PostCard
            key={post.id}
            post={post}
            isCloseFriend={isCloseFriend(post.author_id)}
            onUpdate={handlePostUpdate}
            onDelete={handlePostDelete}
          />
        ))}
        {hasMore && <div ref={sentinelRef} className={styles.loader}><Spinner size={16} /></div>}
      </div>
    </div>
  );
}
