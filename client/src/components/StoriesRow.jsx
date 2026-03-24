import { useCallback, useEffect, useState } from "react";
import { getFeed as getStoryFeed } from "../api/stories";
import { useAuth } from "../contexts/AuthContext";
import Avatar from "./ui/Avatar";
import styles from "./StoriesRow.module.css";

export default function StoriesRow({ onView, onCompose }) {
  const { user } = useAuth();
  const [stories, setStories] = useState([]);

  const fetchStories = useCallback(async () => {
    try {
      const { data } = await getStoryFeed();
      // Group by author
      const grouped = new Map();
      for (const s of data) {
        const key = s.author?.username || s.author_id;
        if (!grouped.has(key)) {
          grouped.set(key, { author: s.author, items: [] });
        }
        grouped.get(key).items.push(s);
      }
      setStories([...grouped.values()]);
    } catch {
      // stories are non-critical
    }
  }, []);

  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  return (
    <div className={styles.row} aria-label="Stories">
      <button className={styles.item} onClick={onCompose} aria-label="Add story">
        <Avatar
          src={user?.avatar_url}
          alt={`@${user?.username}`}
          size={56}
          showPlus
        />
        <span className={styles.label}>Your story</span>
      </button>

      {stories.map((group) => (
        <button
          key={group.author?.username}
          className={styles.item}
          onClick={() => onView(group)}
          aria-label={`View ${group.author?.display_name || group.author?.username}'s story`}
        >
          <Avatar
            src={group.author?.avatar_url}
            alt={`@${group.author?.username}`}
            size={56}
            hasStory
            unseenStory
          />
          <span className={styles.label}>
            {group.author?.display_name || group.author?.username}
          </span>
        </button>
      ))}
    </div>
  );
}
