import { useState, useEffect, useCallback, useRef } from "react";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import Spinner from "../components/ui/Spinner";
import PostCardSkeleton from "../components/PostCardSkeleton";
import * as feedApi from "../api/feed";
import styles from "./Discover.module.css";

const TABS = ["Trending", "News"];

export default function Discover() {
  const [tab, setTab] = useState("Trending");

  return (
    <>
      <Header left={<span>Discover</span>} />
      <div className={styles.container}>
        <nav className={styles.tabs} aria-label="Discover tabs">
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

        {tab === "Trending" && <TrendingList />}
        {tab === "News" && <NewsList />}
      </div>
    </>
  );
}

function TrendingList() {
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
  if (posts.length === 0) return <p className={styles.empty}>No news posts yet. Join news communities to see content here.</p>;

  return (
    <div className={styles.list}>
      {posts.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          onUpdate={handlePostUpdate}
          onDelete={handlePostDelete}
        />
      ))}
      {hasMore && <div ref={sentinelRef} className={styles.loader}><Spinner size={16} /></div>}
    </div>
  );
}
