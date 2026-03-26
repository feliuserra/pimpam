import { useState, useEffect } from "react";
import Spinner from "../../components/ui/Spinner";
import * as notificationsApi from "../../api/notifications";
import styles from "./SettingsForm.module.css";

const TYPES = [
  { key: "follow", label: "New followers" },
  { key: "new_comment", label: "Comments on your posts" },
  { key: "reply", label: "Replies to your comments" },
  { key: "vote", label: "Votes on your posts" },
  { key: "share", label: "Shares of your posts" },
  { key: "mention", label: "Mentions" },
  { key: "community_join", label: "Community joins" },
  { key: "mod_promote", label: "Moderator promotions" },
  { key: "mod_demote", label: "Moderator role changes" },
  { key: "ban_proposal", label: "Ban proposals" },
  { key: "ban_appeal", label: "Ban appeals" },
  { key: "ban_resolved", label: "Ban resolutions" },
  { key: "story_report", label: "Story reports" },
  { key: "welcome", label: "Welcome messages" },
];

export default function NotificationSettings() {
  const [disabled, setDisabled] = useState(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    notificationsApi
      .getPreferences()
      .then((res) => setDisabled(new Set(res.data)))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggle = async (type) => {
    const isCurrentlyDisabled = disabled.has(type);
    // Optimistic update
    setDisabled((prev) => {
      const next = new Set(prev);
      if (isCurrentlyDisabled) next.delete(type);
      else next.add(type);
      return next;
    });
    try {
      await notificationsApi.updatePreference(type, isCurrentlyDisabled);
    } catch {
      // Revert on failure
      setDisabled((prev) => {
        const next = new Set(prev);
        if (isCurrentlyDisabled) next.add(type);
        else next.delete(type);
        return next;
      });
    }
  };

  if (loading) {
    return <div className={styles.loader}><Spinner size={20} /></div>;
  }

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Notification Preferences</h3>
      <p className={styles.hint}>Choose which notifications you receive.</p>
      <div className={styles.toggleList}>
        {TYPES.map(({ key, label }) => (
          <label key={key} className={styles.toggleRow}>
            <span>{label}</span>
            <input
              type="checkbox"
              checked={!disabled.has(key)}
              onChange={() => toggle(key)}
              className={styles.toggle}
            />
          </label>
        ))}
      </div>
    </section>
  );
}
