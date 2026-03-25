import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import Header from "../components/Header";
import PostCard from "../components/PostCard";
import UserCard from "../components/UserCard";
import CommunityCard from "../components/CommunityCard";
import Spinner from "../components/ui/Spinner";
import SearchIcon from "../components/ui/icons/SearchIcon";
import * as searchApi from "../api/search";
import styles from "./Search.module.css";

const TABS = ["All", "Posts", "Users", "Communities"];
const TAB_TO_TYPE = { All: undefined, Posts: "post", Users: "user", Communities: "community" };

export default function Search() {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get("q") || "");
  const [tab, setTab] = useState("All");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const inputRef = useRef(null);

  const activeQuery = params.get("q") || "";

  // Focus input on mount
  useEffect(() => { inputRef.current?.focus(); }, []);

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
          <p className={styles.hint}>Search for posts, users, or communities.</p>
        ) : results.length === 0 ? (
          <p className={styles.empty}>No results for &ldquo;{activeQuery}&rdquo;</p>
        ) : (
          <>
            <p className={styles.count}>{total} result{total !== 1 ? "s" : ""}</p>
            <div className={styles.results}>
              {results.map((hit) => {
                if (hit.username !== undefined) {
                  return <UserCard key={`u-${hit.id}`} user={hit} />;
                }
                if (hit.member_count !== undefined) {
                  return <CommunityCard key={`c-${hit.id}`} community={hit} />;
                }
                return (
                  <PostCard
                    key={`p-${hit.id}`}
                    post={hit}
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
