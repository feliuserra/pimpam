import { useState, useEffect } from "react";
import Spinner from "../../components/ui/Spinner";
import * as friendGroupsApi from "../../api/friendGroups";
import styles from "./SettingsForm.module.css";

export default function FriendGroupSettings() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const loadGroups = async () => {
    try {
      const res = await friendGroupsApi.list();
      setGroups(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadGroups(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (creating || !newName.trim()) return;
    setCreating(true);
    try {
      await friendGroupsApi.create(newName.trim());
      setNewName("");
      await loadGroups();
    } catch {
      // silent
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this friend group?")) return;
    try {
      await friendGroupsApi.remove(id);
      setGroups((prev) => prev.filter((g) => g.id !== id));
    } catch {
      // silent
    }
  };

  const handleRemoveMember = async (groupId, userId) => {
    try {
      await friendGroupsApi.removeMember(groupId, userId);
      // Reload group detail
      const res = await friendGroupsApi.getDetail(groupId);
      setGroups((prev) => prev.map((g) => (g.id === groupId ? res.data : g)));
    } catch {
      // silent
    }
  };

  if (loading) {
    return <div className={styles.loader}><Spinner size={20} /></div>;
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Friend Groups</h3>
      <p className={styles.hint}>
        Control who sees your friends-only posts.
      </p>

      {/* Create form */}
      <form className={styles.inlineForm} onSubmit={handleCreate}>
        <input
          className={styles.input}
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New group name"
          maxLength={50}
        />
        <button type="submit" className={styles.btn} disabled={creating || !newName.trim()}>
          {creating ? "..." : "Create"}
        </button>
      </form>

      {/* Group list */}
      {groups.length === 0 ? (
        <p className={styles.hint}>No friend groups yet.</p>
      ) : (
        <div className={styles.groupList}>
          {groups.map((g) => (
            <div key={g.id} className={styles.groupItem}>
              <div className={styles.groupHeader}>
                <button
                  className={styles.groupName}
                  onClick={() => {
                    if (expanded === g.id) {
                      setExpanded(null);
                    } else {
                      setExpanded(g.id);
                      // Load detail if no members loaded
                      if (!g.members) {
                        friendGroupsApi.getDetail(g.id).then((res) => {
                          setGroups((prev) => prev.map((gr) => (gr.id === g.id ? res.data : gr)));
                        }).catch(() => {});
                      }
                    }
                  }}
                >
                  {g.name}
                  {g.is_close_friends && <span className={styles.badge}>Close Friends</span>}
                  <span className={styles.memberCount}>{g.member_count} member{g.member_count !== 1 ? "s" : ""}</span>
                </button>
                {!g.is_close_friends && (
                  <button className={styles.deleteSmall} onClick={() => handleDelete(g.id)}>
                    Delete
                  </button>
                )}
              </div>

              {expanded === g.id && g.members && (
                <div className={styles.memberList}>
                  {g.members.length === 0 ? (
                    <p className={styles.hint}>No members. Follow users first, then add them.</p>
                  ) : (
                    g.members.map((m) => (
                      <div key={m.user_id} className={styles.memberRow}>
                        <span>@{m.username}</span>
                        <button
                          className={styles.removeBtn}
                          onClick={() => handleRemoveMember(g.id, m.user_id)}
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
