import { useCallback, useEffect, useRef, useState } from "react";
import { getFeed as getStoryFeed, getMine } from "../api/stories";
import { useAuth } from "../contexts/AuthContext";
import { getSeenStories, markStoriesSeen } from "../utils/seenStories";
import styles from "./StoriesRow.module.css";

const SCROLL_PX_PER_SEC = 4; // very gentle drift
const COLLAPSED_KEY = "pimpam_stories_collapsed";

export default function StoriesRow({ onView, onCompose }) {
  const { user } = useAuth();
  const [stories, setStories] = useState([]);
  const [myStories, setMyStories] = useState([]);
  const [seen, setSeen] = useState(() => getSeenStories());
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSED_KEY) === "1");
  const rowRef = useRef(null);
  const scrollingRef = useRef(true);
  const rafRef = useRef(null);

  const fetchStories = useCallback(async () => {
    try {
      const [feedRes, myRes] = await Promise.all([getStoryFeed(), getMine()]);

      // Group feed by author
      const grouped = new Map();
      for (const s of feedRes.data) {
        const key = s.author_username || s.author_id;
        if (!grouped.has(key)) {
          grouped.set(key, {
            author: {
              username: s.author_username,
              avatar_url: s.author_avatar_url,
            },
            items: [],
          });
        }
        grouped.get(key).items.push(s);
      }
      const groups = [...grouped.values()];

      // Sort: unseen groups first, then seen
      const currentSeen = getSeenStories();
      groups.sort((a, b) => {
        const aAllSeen = a.items.every((s) => currentSeen.has(s.id));
        const bAllSeen = b.items.every((s) => currentSeen.has(s.id));
        if (aAllSeen === bAllSeen) return 0;
        return aAllSeen ? 1 : -1;
      });

      setStories(groups);
      setMyStories(myRes.data);
    } catch {
      // stories are non-critical
    }
  }, []);

  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  // Slow auto-scroll — only when content overflows
  useEffect(() => {
    const row = rowRef.current;
    if (!row) return;

    const canScroll = () => row.scrollWidth > row.clientWidth;
    let lastTime = 0;
    let accum = 0;

    const tick = (now) => {
      if (lastTime) {
        const dt = (now - lastTime) / 1000; // seconds
        if (scrollingRef.current && canScroll() && row.scrollLeft < row.scrollWidth - row.clientWidth) {
          accum += SCROLL_PX_PER_SEC * dt;
          if (accum >= 1) {
            const px = Math.floor(accum);
            row.scrollLeft += px;
            accum -= px;
          }
        }
      }
      lastTime = now;
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);

    const pause = () => { scrollingRef.current = false; };
    const resume = () => { scrollingRef.current = true; lastTime = 0; accum = 0; };

    row.addEventListener("pointerdown", pause);
    row.addEventListener("pointerup", resume);
    row.addEventListener("pointerleave", resume);
    row.addEventListener("touchstart", pause, { passive: true });
    row.addEventListener("touchend", resume);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      row.removeEventListener("pointerdown", pause);
      row.removeEventListener("pointerup", resume);
      row.removeEventListener("pointerleave", resume);
      row.removeEventListener("touchstart", pause);
      row.removeEventListener("touchend", resume);
    };
  }, [stories]);

  const handleView = (group) => {
    onView(group);
    const ids = group.items.map((s) => s.id);
    markStoriesSeen(ids);
    setSeen(getSeenStories());
  };

  const handleOwnTap = () => {
    if (myStories.length > 0) {
      // View own stories
      const group = {
        author: { username: user.username, avatar_url: user.avatar_url },
        items: myStories,
      };
      onView(group);
    } else {
      // No stories yet — compose
      onCompose();
    }
  };

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      return next;
    });
  };

  const isGroupSeen = (group) => group.items.every((s) => seen.has(s.id));
  const latestImage = (group) => group.items[0]?.image_url;
  const hasOwnStories = myStories.length > 0;
  const unseenCount = stories.filter((g) => !isGroupSeen(g)).length;

  return (
    <div className={styles.wrapper}>
      <button className={styles.collapseBtn} onClick={toggleCollapsed} aria-label={collapsed ? "Show stories" : "Hide stories"}>
        <span className={styles.collapseLabel}>
          Stories{unseenCount > 0 && !collapsed ? "" : ""}
        </span>
        {collapsed && unseenCount > 0 && (
          <span className={styles.unseenBadge}>{unseenCount} new</span>
        )}
        <span className={`${styles.chevron} ${collapsed ? styles.chevronDown : styles.chevronUp}`}>›</span>
      </button>

      {!collapsed && (
        <div className={styles.row} ref={rowRef} aria-label="Stories">
          {/* Own story */}
          <button className={styles.item} onClick={handleOwnTap} aria-label={hasOwnStories ? "View your story" : "Add story"}>
            <div className={`${styles.thumb} ${hasOwnStories ? styles.ownRing : ""}`}>
              {user?.avatar_url ? (
                <img
                  className={styles.thumbImg}
                  src={user.avatar_url}
                  alt={`@${user.username}`}
                />
              ) : (
                <span className={styles.thumbFallback}>
                  {(user?.username || "?").slice(0, 2).toUpperCase()}
                </span>
              )}
              <span className={styles.addBadge} onClick={(e) => { e.stopPropagation(); onCompose(); }}>+</span>
            </div>
            <span className={styles.label}>Your story</span>
          </button>

          {stories.map((group) => (
            <button
              key={group.author.username}
              className={styles.item}
              onClick={() => handleView(group)}
              aria-label={`View ${group.author.username}'s story`}
            >
              <div className={`${styles.thumb} ${isGroupSeen(group) ? styles.seenRing : styles.unseenRing}`}>
                {latestImage(group) ? (
                  <img
                    className={styles.thumbImg}
                    src={latestImage(group)}
                    alt={`${group.author.username}'s story`}
                  />
                ) : (
                  <span className={styles.thumbFallback}>
                    {(group.author.username || "?").slice(0, 2).toUpperCase()}
                  </span>
                )}
                {group.author.avatar_url && (
                  <img
                    className={styles.avatarOverlay}
                    src={group.author.avatar_url}
                    alt={`@${group.author.username}`}
                  />
                )}
              </div>
              <span className={styles.label}>
                {group.author.username}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
