import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCloseFriends, list as listGroups } from "../../api/friendGroups";
import styles from "./SettingsForm.module.css";

const POST_VIS_KEY = "pimpam_default_post_visibility";
const STORY_VIS_KEY = "pimpam_default_story_visibility";

const VIS_OPTIONS = [
  { value: "public", label: "Public" },
  { value: "followers", label: "Followers" },
  { value: "close_friends", label: "Close Friends" },
];

export default function PrivacySettings() {
  const [postVis, setPostVis] = useState(
    () => localStorage.getItem(POST_VIS_KEY) || "public"
  );
  const [storyVis, setStoryVis] = useState(
    () => localStorage.getItem(STORY_VIS_KEY) || "close_friends"
  );
  const [closeFriendsCount, setCloseFriendsCount] = useState(null);
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    getCloseFriends()
      .then(({ data }) => setCloseFriendsCount(data.member_count))
      .catch(() => setCloseFriendsCount(0));
    listGroups()
      .then(({ data }) => setGroups(data.filter((g) => !g.is_close_friends)))
      .catch(() => setGroups([]));
  }, []);

  return (
    <div>
      <section className={styles.section}>
        <h3 className={styles.heading}>Who sees your posts</h3>
        <p className={styles.hint}>
          This is the default when you create a new post. You can always change it per-post.
        </p>
        <select
          className={styles.input}
          value={postVis}
          onChange={(e) => {
            setPostVis(e.target.value);
            localStorage.setItem(POST_VIS_KEY, e.target.value);
          }}
          aria-label="Default post visibility"
        >
          {VIS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </section>

      <hr className={styles.divider} />

      <section className={styles.section}>
        <h3 className={styles.heading}>Who sees your stories</h3>
        <p className={styles.hint}>
          Stories disappear after their duration expires. By default, only your close friends see them.
        </p>
        <select
          className={styles.input}
          value={storyVis}
          onChange={(e) => {
            setStoryVis(e.target.value);
            localStorage.setItem(STORY_VIS_KEY, e.target.value);
          }}
          aria-label="Default story visibility"
        >
          {[...VIS_OPTIONS].reverse().map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </section>

      <hr className={styles.divider} />

      <section className={styles.section}>
        <h3 className={styles.heading}>Your close friends</h3>
        <p className={styles.hint}>
          {closeFriendsCount != null
            ? `You have ${closeFriendsCount} close friend${closeFriendsCount !== 1 ? "s" : ""}.`
            : "Loading..."}
        </p>
        <p className={styles.hint}>
          Close friends is your inner circle. When you share a story or post with
          &quot;Close Friends&quot;, only the people in this list can see it. They
          won&apos;t know they&apos;re on the list.
        </p>
        <Link to="/friends" className={styles.btn} style={{ textDecoration: "none", display: "inline-block" }}>
          Manage close friends
        </Link>
      </section>

      <hr className={styles.divider} />

      <section className={styles.section}>
        <h3 className={styles.heading}>Friend groups</h3>
        {groups.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
            {groups.map((g) => (
              <li key={g.id} style={{ fontSize: "0.88rem", marginBottom: 4 }}>
                {g.name} ({g.member_count} member{g.member_count !== 1 ? "s" : ""})
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.hint}>No friend groups created yet.</p>
        )}
        <p className={styles.hint} style={{ marginTop: 8 }}>
          Friend groups let you organize the people you follow into lists. You can
          share specific posts with a group — only members of that group will see them.
        </p>
        <Link to="/settings/friend-groups" className={styles.btn} style={{ textDecoration: "none", display: "inline-block", marginTop: 8 }}>
          Manage friend groups
        </Link>
      </section>
    </div>
  );
}
