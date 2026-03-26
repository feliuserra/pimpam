import { useState, useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import UserCard from "../components/UserCard";
import CommunityCard from "../components/CommunityCard";
import Spinner from "../components/ui/Spinner";
import SearchIcon from "../components/ui/icons/SearchIcon";
import { useCloseFriends } from "../contexts/CloseFriendsContext";
import * as searchApi from "../api/search";
import * as hashtagsApi from "../api/hashtags";
import styles from "./Search.module.css";

const TABS = ["All", "Posts", "Users", "Communities", "Hashtags"];
const TAB_TO_TYPE = { All: undefined, Posts: "post", Users: "user", Communities: "community", Hashtags: "hashtag" };

export default function Search() {
  const { isCloseFriend } = useCloseFriends();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") || "");
  const [tab, setTab] = useState(params.get("type") === "hashtag" ? "Hashtags" : "All");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [trending, setTrending] = useState([]);
  const inputRef = useRef(null);

  const activeQuery = params.get("q") || "";

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

  // Load trending hashtags when there's no query
  useEffect(() => {
    if (activeQuery) return;
    hashtagsApi.trending(10).then((res) => setTrending(res.data || [])).catch(() => {});
  }, [activeQuery]);

  // Fetch results when query or tab changes
  useEffect(() => {
    if (!activeQuery) { setResults([]); setTotal(0); return; }
    let cancelled = false;
    setLoading(true);
    searchApi
      .search({ q: activeQuery, type: TAB_TO_TYPE[tab], limit: 50 })
      .then((res) => {
        if (cancelled) return;
        setResults(res.data.hits || []);
        setTotal(res.data.total || 0);
      })
      .catch(() => { if (!cancelled) setResults([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [activeQuery, tab]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = query.trim();
    if (q) setParams({ q });
  };

  const handlePostDelete = (id) =>
    setResults((prev) => prev.filter((r) => r.id !== id));

  return (
    <>
      <Header left={<span>Search</span>} />

      <div className={styles.container}>
        {/* Search bar */}
        <form className={styles.searchBar} onSubmit={handleSubmit}>
          <SearchIcon size={16} />
          <input
            ref={inputRef}
            className={styles.input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search posts, users, communities..."
            type="search"
          />
        </form>

        {/* Tabs */}
        {activeQuery && (
          <nav className={styles.tabs} aria-label="Search type filter">
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
        )}

        {/* Results */}
        {loading ? (
          <div className={styles.loader}><Spinner size={24} /></div>
        ) : !activeQuery ? (
          <div>
            <p className={styles.hint}>Search for posts, users, communities, or hashtags.</p>
            {trending.length > 0 && (
              <div className={styles.trendingSection}>
                <h3 className={styles.trendingTitle}>Trending hashtags</h3>
                <div className={styles.trendingList}>
                  {trending.map((tag) => (
                    <Link
                      key={tag.id}
                      to={`/tag/${tag.name}`}
                      className={styles.trendingTag}
                    >
                      <span className={styles.trendingName}>#{tag.name}</span>
                      <span className={styles.trendingCount}>{tag.post_count} {tag.post_count === 1 ? "post" : "posts"}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : results.length === 0 ? (
          <p className={styles.empty}>No results for &ldquo;{activeQuery}&rdquo;</p>
        ) : (
          <>
            <p className={styles.count}>{total} result{total !== 1 ? "s" : ""}</p>
            <div className={styles.results}>
              {results.map((hit) => {
                if (hit.type === "hashtag") {
                  return (
                    <Link
                      key={`h-${hit.id}`}
                      to={`/tag/${hit.name}`}
                      className={styles.hashtagResult}
                    >
                      <span className={styles.hashtagName}>#{hit.name}</span>
                      <span className={styles.hashtagCount}>{hit.post_count} {hit.post_count === 1 ? "post" : "posts"}</span>
                    </Link>
                  );
                }
                if (hit.username !== undefined) {
                  return <UserCard key={`u-${hit.id}`} user={hit} isCloseFriend={isCloseFriend(hit.id)} />;
                }
                if (hit.member_count !== undefined) {
                  return <CommunityCard key={`c-${hit.id}`} community={hit} />;
                }
                return (
                  <PostCard
                    key={`p-${hit.id}`}
                    post={hit}
                    isCloseFriend={isCloseFriend(hit.author_id)}
                    onDelete={handlePostDelete}
                  />
                );
              })}
            </div>
          </>
        )}
      </div>
    </>
  );
}
