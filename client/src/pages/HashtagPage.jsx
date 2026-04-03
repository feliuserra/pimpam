import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import Spinner from "../components/ui/Spinner";
import { useAuth } from "../contexts/AuthContext";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import { useToast } from "../contexts/ToastContext";
import errorMessage from "../api/errorMessage";
import * as hashtagsApi from "../api/hashtags";
import styles from "./HashtagPage.module.css";

export default function HashtagPage() {
  const { user } = useAuth();
  const { isCloseFriend } = useCloseFriends();
  const { addToast } = useToast();
  const { name } = useParams();
  const [hashtag, setHashtag] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [subBusy, setSubBusy] = useState(false);
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
        setIsSubscribed(tagRes.data.is_subscribed || false);
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

  const toggleSubscription = async () => {
    if (subBusy) return;
    setSubBusy(true);
    const wasSub = isSubscribed;
    setIsSubscribed(!wasSub);
    try {
      if (wasSub) {
        await hashtagsApi.unsubscribe(name);
      } else {
        await hashtagsApi.subscribe(name);
      }
    } catch {
      setIsSubscribed(wasSub);
      addToast(wasSub ? "Couldn't unfollow this hashtag. Try again." : "Couldn't follow this hashtag. Try again.", "error");
    } finally {
      setSubBusy(false);
    }
  };

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
          <div className={styles.headerTop}>
            <h1 className={styles.name}>#{hashtag?.name}</h1>
            {user && (
              <button
                className={`${styles.followBtn} ${isSubscribed ? styles.following : ""}`}
                onClick={toggleSubscription}
                disabled={subBusy}
              >
                {isSubscribed ? "Following" : "Follow"}
              </button>
            )}
          </div>
          <span className={styles.count}>
            {hashtag?.post_count} {hashtag?.post_count === 1 ? "post" : "posts"}
            {hashtag?.subscriber_count > 0 && (
              <> &middot; {hashtag.subscriber_count} {hashtag.subscriber_count === 1 ? "follower" : "followers"}</>
            )}
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
