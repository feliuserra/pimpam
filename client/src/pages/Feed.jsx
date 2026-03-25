import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import PostCard from "../components/PostCard";
import StoriesRow from "../components/StoriesRow";
import StoryViewer from "../components/StoryViewer";
import StoryCompose from "../components/StoryCompose";
import ComposePost from "../components/ComposePost";
import Spinner from "../components/ui/Spinner";
import PostCardSkeleton from "../components/PostCardSkeleton";
import PlusIcon from "../components/ui/icons/PlusIcon";
import SearchIcon from "../components/ui/icons/SearchIcon";
import TrendingIcon from "../components/ui/icons/TrendingIcon";
import { useInfiniteList } from "../hooks/useInfiniteList";
import { useWS } from "../contexts/WSContext";
import { getFeed } from "../api/feed";
import * as friendGroupsApi from "../api/friendGroups";
import styles from "./Feed.module.css";

export default function Feed() {
  const navigate = useNavigate();
  const [composeOpen, setComposeOpen] = useState(false);
  const [storyComposeOpen, setStoryComposeOpen] = useState(false);
  const [viewingStory, setViewingStory] = useState(null);
  const [newPostsBanner, setNewPostsBanner] = useState(false);
  const [pullY, setPullY] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [closeFriendIds, setCloseFriendIds] = useState(new Set());
  const touchStartY = useRef(0);
  const pulling = useRef(false);

  useEffect(() => {
    friendGroupsApi.getCloseFriends()
      .then((res) => {
        const ids = new Set((res.data?.members || []).map((m) => m.user_id));
        setCloseFriendIds(ids);
      })
      .catch(() => {});
  }, []);

  const fetchFeed = useCallback(
    (cursor) => getFeed({ limit: 20, before_id: cursor }),
    [],
  );

  const { items: posts, setItems: setPosts, loading, hasMore, sentinelRef, refresh } =
    useInfiniteList(fetchFeed);

  useWS(
    "new_post",
    useCallback(() => {
      setNewPostsBanner(true);
    }, []),
  );

  const handleNewPostsBanner = async () => {
    setNewPostsBanner(false);
    await refresh();
  };

  const handlePostCreated = (post) => {
    setPosts((prev) => [post, ...prev]);
  };

  return (
    <>
      <header className={styles.brandHeader}>
        <button className={styles.brandName} onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); refresh(); }}>
          ピムパム
        </button>
      </header>

      <div className={styles.searchBar}>
        <button className={styles.searchPill} onClick={() => navigate("/search")}>
          <SearchIcon size={16} />
          <span>Search...</span>
        </button>
        <button
          className={styles.iconBtn}
          onClick={() => navigate("/discover")}
          aria-label="Discover"
        >
          <TrendingIcon size={20} />
        </button>
        <button
          className={styles.iconBtn}
          onClick={() => setComposeOpen(true)}
          aria-label="New post"
        >
          <PlusIcon size={20} />
        </button>
      </div>

      <div
        className={styles.container}
        onTouchStart={(e) => {
          if (window.scrollY === 0) {
            touchStartY.current = e.touches[0].clientY;
            pulling.current = true;
          }
        }}
        onTouchMove={(e) => {
          if (!pulling.current) return;
          const dy = e.touches[0].clientY - touchStartY.current;
          if (dy > 0 && window.scrollY === 0) {
            setPullY(Math.min(dy * 0.4, 80));
          } else {
            setPullY(0);
          }
        }}
        onTouchEnd={async () => {
          if (!pulling.current) return;
          pulling.current = false;
          if (pullY > 50) {
            setRefreshing(true);
            setPullY(40);
            await refresh();
            setRefreshing(false);
          }
          setPullY(0);
        }}
      >
        {pullY > 0 && (
          <div className={styles.pullIndicator} style={{ height: pullY }}>
            {refreshing ? (
              <Spinner size={18} />
            ) : (
              <span style={{ opacity: Math.min(pullY / 50, 1), fontSize: "0.8rem", color: "var(--color-text-muted)" }}>
                {pullY > 50 ? "Release to refresh" : "Pull to refresh"}
              </span>
            )}
          </div>
        )}

        <StoriesRow
          onCompose={() => setStoryComposeOpen(true)}
          onView={(group) => setViewingStory(group)}
        />

        {newPostsBanner && (
          <button className={styles.banner} onClick={handleNewPostsBanner}>
            New posts available
          </button>
        )}

        {posts.length === 0 && loading && (
          <div aria-label="Loading feed">
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
            <PostCardSkeleton />
          </div>
        )}

        {posts.length === 0 && !loading && (
          <div className={styles.empty}>
            <p>Nothing here yet.</p>
            <p>Follow people or join a community to see posts!</p>
          </div>
        )}

        <section aria-label="Feed">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              isCloseFriend={closeFriendIds.has(post.author_id)}
              onDelete={(id) => setPosts((prev) => prev.filter((p) => p.id !== id))}
              onUpdate={(updated) =>
                setPosts((prev) =>
                  prev.map((p) => (p.id === updated.id ? updated : p)),
                )
              }
            />
          ))}
        </section>

        {hasMore && (
          <div ref={sentinelRef} className={styles.sentinel}>
            {loading && posts.length > 0 && <Spinner size={24} />}
          </div>
        )}
      </div>

      <button
        className={styles.fab}
        onClick={() => setComposeOpen(true)}
        aria-label="Create post"
      >
        <PlusIcon size={24} />
      </button>

      <ComposePost
        open={composeOpen}
        onClose={() => setComposeOpen(false)}
        onCreated={handlePostCreated}
      />

      <StoryCompose
        open={storyComposeOpen}
        onClose={() => setStoryComposeOpen(false)}
      />

      {viewingStory && (
        <StoryViewer
          group={viewingStory}
          onClose={() => setViewingStory(null)}
        />
      )}
    </>
  );
}
