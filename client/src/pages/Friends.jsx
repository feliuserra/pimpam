import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import UserCard from "../components/UserCard";
import Spinner from "../components/ui/Spinner";
import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";
import * as friendGroupsApi from "../api/friendGroups";
import styles from "./Friends.module.css";

const TABS = ["Following", "Followers", "Groups", "Suggestions"];

export default function Friends() {
  const { user: me } = useAuth();
  const [tab, setTab] = useState("Following");

  return (
    <>
      <Header left={<span>Friends</span>} />
      <div className={styles.container}>
        <nav className={styles.tabs} aria-label="Friends tabs">
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

        {tab === "Following" && <FollowList username={me?.username} type="following" hideFollow />}
        {tab === "Followers" && <FollowList username={me?.username} type="followers" />}
        {tab === "Groups" && <GroupsList />}
        {tab === "Suggestions" && <SuggestionsList />}
      </div>
    </>
  );
}

function FollowList({ username, type, hideFollow = false }) {
  const [users, setUsers] = useState([]);
  const [closeFriendIds, setCloseFriendIds] = useState(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) return;
    setLoading(true);
    const fetcher = type === "followers" ? usersApi.getFollowers : usersApi.getFollowing;
    const promises = [fetcher(username, { limit: 100 })];
    if (type === "following") {
      promises.push(friendGroupsApi.getCloseFriends().catch(() => ({ data: { members: [] } })));
    }
    Promise.all(promises)
      .then(([usersRes, cfRes]) => {
        const cfIds = new Set((cfRes?.data?.members || []).map((m) => m.user_id));
        setCloseFriendIds(cfIds);
        // Sort close friends first in the following list
        const sorted = [...usersRes.data].sort((a, b) => {
          const aClose = cfIds.has(a.id);
          const bClose = cfIds.has(b.id);
          if (aClose === bClose) return 0;
          return aClose ? -1 : 1;
        });
        setUsers(sorted);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [username, type]);

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;
  if (users.length === 0) return <p className={styles.empty}>No {type} yet.</p>;

  return (
    <div className={styles.list}>
      {users.map((u) => (
        <UserCard key={u.id} user={u} hideFollow={hideFollow} isCloseFriend={closeFriendIds.has(u.id)} />
      ))}
    </div>
  );
}

function GroupsList() {
  const { user: me } = useAuth();
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [detail, setDetail] = useState(null);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [following, setFollowing] = useState([]);
  const [addQuery, setAddQuery] = useState("");
  const [adding, setAdding] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  const loadGroups = useCallback(async () => {
    try {
      const res = await friendGroupsApi.list();
      setGroups(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  // Load people you follow (for the add member picker)
  useEffect(() => {
    if (!me?.username) return;
    usersApi.getFollowing(me.username, { limit: 200 })
      .then((res) => setFollowing(res.data))
      .catch(() => {});
  }, [me?.username]);

  useEffect(() => { loadGroups(); }, [loadGroups]);

  const handleCreate = async (e) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      await friendGroupsApi.create(name);
      setNewName("");
      await loadGroups();
    } catch {
      // silent
    } finally {
      setCreating(false);
    }
  };

  const handleExpand = async (groupId) => {
    if (expanded === groupId) {
      setExpanded(null);
      setDetail(null);
      setAddQuery("");
      setSelectedUser(null);
      return;
    }
    setExpanded(groupId);
    try {
      const res = await friendGroupsApi.getDetail(groupId);
      setDetail(res.data);
    } catch {
      // silent
    }
  };

  const handleAddMember = async (groupId, userId) => {
    if (adding) return;
    setAdding(true);
    try {
      const res = await friendGroupsApi.addMember(groupId, userId);
      setDetail(res.data);
      setAddQuery("");
      setSelectedUser(null);
      await loadGroups();
    } catch {
      // silent
    } finally {
      setAdding(false);
    }
  };

  const handleRemoveMember = async (groupId, userId) => {
    try {
      await friendGroupsApi.removeMember(groupId, userId);
      // Refresh detail
      const res = await friendGroupsApi.getDetail(groupId);
      setDetail(res.data);
      await loadGroups();
    } catch {
      // silent
    }
  };

  const handleDeleteGroup = async (groupId) => {
    try {
      await friendGroupsApi.remove(groupId);
      setExpanded(null);
      setDetail(null);
      await loadGroups();
    } catch {
      // silent
    }
  };

  // Filter following list: exclude current members, match by query
  const availableToAdd = (members) => {
    const memberIds = new Set((members || []).map((m) => m.user_id));
    return following.filter(
      (u) => !memberIds.has(u.id) && (
        !addQuery ||
        u.username.toLowerCase().includes(addQuery.toLowerCase()) ||
        (u.display_name || "").toLowerCase().includes(addQuery.toLowerCase())
      )
    );
  };

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;

  return (
    <div className={styles.list}>
      <form className={styles.createGroup} onSubmit={handleCreate}>
        <input
          className={styles.createInput}
          type="text"
          placeholder="New group name..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          maxLength={50}
        />
        <button
          className={styles.createBtn}
          type="submit"
          disabled={!newName.trim() || creating}
        >
          {creating ? "Creating..." : "Create"}
        </button>
      </form>
      {groups.length === 0 && <p className={styles.empty}>No friend groups yet.</p>}
      {groups.map((g) => (
        <div key={g.id} className={styles.groupCard}>
          <button className={styles.groupHeader} onClick={() => handleExpand(g.id)}>
            <div>
              <span className={styles.groupName}>{g.name}</span>
              {g.is_close_friends && <span className={styles.closeBadge}>Close Friends</span>}
            </div>
            <span className={styles.groupCount}>{g.member_count} members</span>
          </button>
          {expanded === g.id && detail && (
            <div className={styles.groupDetail}>
              {/* Current members */}
              <div className={styles.membersList}>
                {detail.members.length === 0 ? (
                  <p className={styles.emptySmall}>No members yet. Add people you follow below.</p>
                ) : (
                  detail.members.map((m) => (
                    <div key={m.user_id} className={styles.memberRow}>
                      <Link to={`/u/${m.username}`} className={styles.memberLink}>
                        @{m.username}
                      </Link>
                      <button
                        className={styles.removeBtn}
                        onClick={() => handleRemoveMember(g.id, m.user_id)}
                        aria-label={`Remove ${m.username}`}
                      >
                        &times;
                      </button>
                    </div>
                  ))
                )}
              </div>

              {/* Add member */}
              <div className={styles.addMemberSection}>
                {selectedUser ? (
                  <div className={styles.confirmRow}>
                    <span className={styles.selectedName}>@{selectedUser.username}</span>
                    <div className={styles.confirmActions}>
                      <button
                        className={styles.confirmBtn}
                        onClick={() => handleAddMember(g.id, selectedUser.id)}
                        disabled={adding}
                      >
                        {adding ? "Adding..." : "Confirm"}
                      </button>
                      <button
                        className={styles.cancelBtn}
                        onClick={() => setSelectedUser(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <input
                      className={styles.addMemberInput}
                      type="text"
                      placeholder="Search people you follow..."
                      value={addQuery}
                      onChange={(e) => setAddQuery(e.target.value)}
                    />
                    {addQuery && (
                      <div className={styles.addMemberResults}>
                        {availableToAdd(detail.members).slice(0, 5).map((u) => (
                          <button
                            key={u.id}
                            className={styles.addMemberOption}
                            onClick={() => setSelectedUser(u)}
                          >
                            <span>@{u.username}</span>
                          </button>
                        ))}
                        {availableToAdd(detail.members).length === 0 && (
                          <p className={styles.emptySmall}>No matches</p>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Delete group */}
              {!g.is_close_friends && (
                <button
                  className={styles.deleteGroupBtn}
                  onClick={() => handleDeleteGroup(g.id)}
                >
                  Delete group
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function SuggestionsList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    usersApi.getSuggestions()
      .then((res) => setUsers(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;
  if (users.length === 0) return <p className={styles.empty}>No suggestions right now. Follow more people to get recommendations!</p>;

  return (
    <div className={styles.list}>
      <p className={styles.hint}>People followed by your friends</p>
      {users.map((u) => <UserCard key={u.id} user={u} />)}
    </div>
  );
}
