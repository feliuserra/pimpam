import { useEffect, useState } from "react";
import api from "../api/client";
import PostCard from "../components/PostCard";
import styles from "./Feed.module.css";

export default function Feed() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [beforeId, setBeforeId] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  const fetchPosts = async (cursor = null) => {
    try {
      const params = { limit: 20, ...(cursor && { before_id: cursor }) };
      const { data } = await api.get("/feed", { params });
      setPosts((prev) => (cursor ? [...prev, ...data] : data));
      setHasMore(data.length === 20);
      if (data.length > 0) setBeforeId(data.at(-1).id);
    } catch {
      setError("Could not load feed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPosts(); }, []);

  if (loading) return <p className={styles.status}>Loading…</p>;
  if (error) return <p className={styles.status}>{error}</p>;
  if (posts.length === 0) return <p className={styles.status}>Nothing here yet. Follow some people!</p>;

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <h1>PimPam</h1>
      </header>

      <section aria-label="Feed">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </section>

      {hasMore && (
        <button
          className={styles.loadMore}
          onClick={() => fetchPosts(beforeId)}
        >
          Load more
        </button>
      )}
    </main>
  );
}
