import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import StoriesRow from "../components/StoriesRow";
import StoryViewer from "../components/StoryViewer";
import StoryCompose from "../components/StoryCompose";
import ComposePost from "../components/ComposePost";
import Spinner from "../components/ui/Spinner";
import PlusIcon from "../components/ui/icons/PlusIcon";
import SearchIcon from "../components/ui/icons/SearchIcon";
import { useInfiniteList } from "../hooks/useInfiniteList";
import { useWS } from "../contexts/WSContext";
import { getFeed } from "../api/feed";
import styles from "./Feed.module.css";

export default function Feed() {
  const navigate = useNavigate();
  const [composeOpen, setComposeOpen] = useState(false);
  const [storyComposeOpen, setStoryComposeOpen] = useState(false);
  const [viewingStory, setViewingStory] = useState(null);
  const [newPostsBanner, setNewPostsBanner] = useState(false);

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
      <Header
        left={<span>PimPam</span>}
        right={
          <>
            <button className={styles.iconBtn} aria-label="Search" onClick={() => navigate("/search")}>
              <SearchIcon size={20} />
            </button>
            <button
              className={styles.iconBtn}
              onClick={() => setComposeOpen(true)}
              aria-label="New post"
            >
              <PlusIcon size={20} />
            </button>
          </>
        }
      />

      <div className={styles.container}>
        <StoriesRow
          onCompose={() => setStoryComposeOpen(true)}
          onView={(group) => setViewingStory(group)}
        />

        {newPostsBanner && (
          <button className={styles.banner} onClick={handleNewPostsBanner}>
            New posts available
          </button>
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
            {loading && <Spinner size={24} />}
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
