import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import CommunityCard from "../components/CommunityCard";
import CreateCommunityModal from "../components/CreateCommunityModal";
import SearchIcon from "../components/ui/icons/SearchIcon";
import PlusIcon from "../components/ui/icons/PlusIcon";
import { useAuth } from "../contexts/AuthContext";
import * as communitiesApi from "../api/communities";
import styles from "./Communities.module.css";

const JOINED_PAGE_SIZE = 10;
const DISCOVER_SIZES = [10, 20, 50];

export default function Communities() {
  const { user } = useAuth();
  const [joined, setJoined] = useState([]);
  const [discover, setDiscover] = useState([]);
  const [sort, setSort] = useState("popular");
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [joinedPage, setJoinedPage] = useState(0);
  const [discoverSize, setDiscoverSize] = useState(20);
  const [discoverPage, setDiscoverPage] = useState(0);

  // Load joined communities once
  useEffect(() => {
    if (!user) { setJoined([]); return; }
    communitiesApi.listJoined().then((r) => setJoined(r.data)).catch(() => {});
  }, [user]);

  // Load discover communities (server-side search)
  const searchTimer = useRef(null);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 250);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = { sort, limit: 200 };
    if (debouncedSearch) params.q = debouncedSearch;
    communitiesApi.list(params)
      .then((res) => { if (!cancelled) setDiscover(res.data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [sort, debouncedSearch]);

  // Reset pages when sort/size/search changes
  useEffect(() => { setDiscoverPage(0); }, [sort, discoverSize, debouncedSearch]);
  useEffect(() => { setJoinedPage(0); }, [search]);

  const joinedIds = new Set(joined.map((c) => c.id));

  const handleJoinChange = (communityId, didJoin) => {
    if (didJoin) {
      const community = discover.find((c) => c.id === communityId);
      if (community && !joinedIds.has(communityId)) {
        setJoined((prev) => [...prev, community]);
      }
    } else {
      setJoined((prev) => prev.filter((c) => c.id !== communityId));
    }
  };

  // Paginated slices — joined filtered client-side, discover filtered server-side
  const joinedFiltered = search
    ? joined.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : joined;
  const joinedTotal = joinedFiltered.length;
  const joinedTotalPages = Math.ceil(joinedTotal / JOINED_PAGE_SIZE);
  const joinedSlice = joinedFiltered.slice(
    joinedPage * JOINED_PAGE_SIZE,
    (joinedPage + 1) * JOINED_PAGE_SIZE,
  );

  const discoverTotal = discover.length;
  const discoverTotalPages = Math.ceil(discoverTotal / discoverSize);
  const discoverSlice = discover.slice(
    discoverPage * discoverSize,
    (discoverPage + 1) * discoverSize,
  );

  return (
    <>
      <Header
        left={<span>Communities</span>}
        right={
          <div className={styles.searchPill}>
            <SearchIcon size={14} />
            <input
              className={styles.searchInput}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search communities..."
            />
          </div>
        }
      />

      <div className={styles.container}>
        {/* Your communities */}
        {user && joined.length > 0 && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Your communities</h2>
            {joinedFiltered.length === 0 && search ? (
              <p className={styles.empty}>No joined communities match &ldquo;{search}&rdquo;</p>
            ) : (
              <>
                <div className={styles.grid}>
                  {joinedSlice.map((c) => (
                    <Link key={c.id} to={`/c/${c.name}`} className={styles.gridItem}>
                      <Avatar
                        src={c.avatar_url}
                        alt={c.name}
                        size={52}
                      />
                      <span className={styles.gridName}>c/{c.name}</span>
                      {c.user_role && c.user_role !== "member" && (
                        <span className={`${styles.roleBadge} ${styles[`role_${c.user_role}`] || ""}`}>
                          {c.user_role === "owner" ? "Owner" : c.user_role === "senior_mod" ? "Sr. Mod" : c.user_role === "moderator" ? "Mod" : c.user_role === "trusted_member" ? "Trusted" : c.user_role}
                        </span>
                      )}
                    </Link>
                  ))}
                  <button
                    className={styles.gridCreate}
                    onClick={() => setCreateOpen(true)}
                  >
                    <span className={styles.createCircle}>
                      <PlusIcon size={20} />
                    </span>
                    <span className={styles.gridName}>Create</span>
                  </button>
                </div>
                {joinedTotalPages > 1 && (
                  <div className={styles.pagination}>
                    <button
                      className={styles.pageBtn}
                      onClick={() => setJoinedPage((p) => p - 1)}
                      disabled={joinedPage === 0}
                    >
                      Prev
                    </button>
                    <span className={styles.pageInfo}>
                      {joinedPage + 1} / {joinedTotalPages}
                    </span>
                    <button
                      className={styles.pageBtn}
                      onClick={() => setJoinedPage((p) => p + 1)}
                      disabled={joinedPage >= joinedTotalPages - 1}
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {user && joined.length === 0 && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Your communities</h2>
            <div className={styles.emptyCard}>
              <p className={styles.emptyText}>
                You haven't joined any communities yet.
              </p>
              <button className={styles.createBtn} onClick={() => setCreateOpen(true)}>
                + Create community
              </button>
            </div>
          </section>
        )}

        {/* Discover */}
        <section className={styles.section}>
          <div className={styles.discoverHeader}>
            <h2 className={styles.sectionTitle}>Discover</h2>
            <div className={styles.discoverControls}>
              <div className={styles.sizeToggle}>
                {DISCOVER_SIZES.map((s) => (
                  <button
                    key={s}
                    className={`${styles.sizeBtn} ${discoverSize === s ? styles.active : ""}`}
                    onClick={() => setDiscoverSize(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div className={styles.sortToggle}>
                {["popular", "newest"].map((s) => (
                  <button
                    key={s}
                    className={`${styles.sortBtn} ${sort === s ? styles.active : ""}`}
                    onClick={() => setSort(s)}
                  >
                    {s === "popular" ? "Popular" : "New"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {loading ? (
            <div className={styles.loader}><Spinner size={20} /></div>
          ) : discover.length === 0 ? (
            <p className={styles.empty}>
              {search ? "No communities match your search." : "No communities yet."}
            </p>
          ) : (
            <>
              {discoverSlice.map((c) => (
                <CommunityCard
                  key={c.id}
                  community={c}
                  isJoined={joinedIds.has(c.id)}
                  onJoinChange={handleJoinChange}
                />
              ))}
              {discoverTotalPages > 1 && (
                <div className={styles.pagination}>
                  <button
                    className={styles.pageBtn}
                    onClick={() => setDiscoverPage((p) => p - 1)}
                    disabled={discoverPage === 0}
                  >
                    Prev
                  </button>
                  <span className={styles.pageInfo}>
                    {discoverPage + 1} / {discoverTotalPages}
                  </span>
                  <button
                    className={styles.pageBtn}
                    onClick={() => setDiscoverPage((p) => p + 1)}
                    disabled={discoverPage >= discoverTotalPages - 1}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      <CreateCommunityModal
        open={createOpen}
        onClose={() => {
          setCreateOpen(false);
          // Refresh joined list
          if (user) communitiesApi.listJoined().then((r) => setJoined(r.data)).catch(() => {});
        }}
      />
    </>
  );
}
