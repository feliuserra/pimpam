import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import Spinner from "../components/ui/Spinner";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import * as hashtagsApi from "../api/hashtags";
import styles from "./HashtagPage.module.css";

export default function HashtagPage() {
  const { isCloseFriend } = useCloseFriends();
  const { name } = useParams();
  const [hashtag, setHashtag] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);
  const sentinel = useRef(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setPosts([]);
    setHasMore(true);
    Promise.all([
      hashtagsApi.getHashtag(name),
      hashtagsApi.getPostsByHashtag(name, { limit: 20 }),
    ])
      .then(([tagRes, postsRes]) => {
        setHashtag(tagRes.data);
        setPosts(postsRes.data || []);
        setHasMore((postsRes.data || []).length >= 20);
      })
      .catch(() => setError("Hashtag not found"))
      .finally(() => setLoading(false));
  }, [name]);

  const loadMore = useCallback(() => {
    if (loadingMore || !hasMore || posts.length === 0) return;
    setLoadingMore(true);
    const lastId = posts[posts.length - 1].id;
    hashtagsApi
      .getPostsByHashtag(name, { limit: 20, before_id: lastId })
      .then((res) => {
        const newPosts = res.data || [];
        setPosts((prev) => [...prev, ...newPosts]);
        setHasMore(newPosts.length >= 20);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  }, [name, posts, loadingMore, hasMore]);

  // Infinite scroll
  useEffect(() => {
    if (!sentinel.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMore(); },
      { rootMargin: "200px" }
    );
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [loadMore]);

  const handlePostDelete = (id) =>
    setPosts((prev) => prev.filter((p) => p.id !== id));

  if (loading) {
    return (
      <>
        <Header left={<span>#{name}</span>} />
        <div className={styles.loader}><Spinner size={24} /></div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Header left={<span>Hashtag</span>} />
        <p className={styles.error}>{error}</p>
      </>
    );
  }

  return (
    <>
      <Header left={<span>#{name}</span>} />
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.name}>#{hashtag?.name}</h1>
          <span className={styles.count}>
            {hashtag?.post_count} {hashtag?.post_count === 1 ? "post" : "posts"}
          </span>
        </div>

        {posts.length === 0 ? (
          <p className={styles.empty}>No posts with this hashtag yet.</p>
        ) : (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              isCloseFriend={isCloseFriend(post.author_id)}
              onDelete={handlePostDelete}
            />
          ))
        )}

        <div ref={sentinel} className={styles.sentinel}>
          {loadingMore && <Spinner size={20} />}
        </div>
      </div>
    </>
  );
}
