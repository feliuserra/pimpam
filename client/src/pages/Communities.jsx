import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Spinner from "../components/ui/Spinner";
import CommunityCard from "../components/CommunityCard";
import CreateCommunityModal from "../components/CreateCommunityModal";
import SearchIcon from "../components/ui/icons/SearchIcon";
import { useAuth } from "../contexts/AuthContext";
import * as communitiesApi from "../api/communities";
import styles from "./Communities.module.css";

export default function Communities() {
  const { user } = useAuth();
  const [joined, setJoined] = useState([]);
  const [discover, setDiscover] = useState([]);
  const [sort, setSort] = useState("popular");
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const promises = [
      communitiesApi.list({ sort, limit: 50 }),
    ];
    if (user) promises.push(communitiesApi.listJoined());

    Promise.all(promises)
      .then(([allRes, joinedRes]) => {
        if (cancelled) return;
        setDiscover(allRes.data);
        if (joinedRes) setJoined(joinedRes.data);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [sort, user]);

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

  const filtered = search
    ? discover.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : discover;

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
            <div className={styles.scroll}>
              {joined.map((c) => (
                <Link key={c.id} to={`/c/${c.name}`} className={styles.chip}>
                  c/{c.name}
                </Link>
              ))}
              <button
                className={styles.createChip}
                onClick={() => setCreateOpen(true)}
              >
                + Create
              </button>
            </div>
          </section>
        )}

        {user && joined.length === 0 && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Your communities</h2>
            <p className={styles.empty}>
              You haven't joined any communities yet.{" "}
              <button className={styles.link} onClick={() => setCreateOpen(true)}>
                Create one
              </button>
            </p>
          </section>
        )}

        {/* Discover */}
        <section className={styles.section}>
          <div className={styles.discoverHeader}>
            <h2 className={styles.sectionTitle}>Discover</h2>
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

          {loading ? (
            <div className={styles.loader}><Spinner size={20} /></div>
          ) : filtered.length === 0 ? (
            <p className={styles.empty}>
              {search ? "No communities match your search." : "No communities yet."}
            </p>
          ) : (
            filtered.map((c) => (
              <CommunityCard
                key={c.id}
                community={c}
                isJoined={joinedIds.has(c.id)}
                onJoinChange={handleJoinChange}
              />
            ))
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
