import { useState } from "react";
import Avatar from "../../components/ui/Avatar";
import { useAuth } from "../../contexts/AuthContext";
import * as usersApi from "../../api/users";
import * as mediaApi from "../../api/media";
import styles from "./SettingsForm.module.css";

export default function ProfileSettings() {
  const { user, updateUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus(null);
    try {
      const res = await mediaApi.upload(file, "avatar");
      setAvatarPreview(res.data.url);
    } catch {
      setStatus({ type: "error", msg: "Failed to upload image" });
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setStatus(null);
    try {
      const res = await usersApi.updateMe({
        display_name: displayName || null,
        bio: bio || null,
        avatar_url: avatarPreview || null,
      });
      updateUser(res.data);
      setStatus({ type: "success", msg: "Profile updated." });
    } catch {
      setStatus({ type: "error", msg: "Failed to save profile" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={styles.section}>
      <h3 className={styles.heading}>Profile</h3>
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.avatarRow}>
          <Avatar src={avatarPreview} alt={`@${user?.username}`} size={72} />
          <label className={styles.uploadLabel}>
            {uploading ? "Uploading..." : "Change photo"}
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleAvatarChange}
              className={styles.fileInput}
              disabled={uploading}
            />
          </label>
        </div>

        <label className={styles.label}>
          Display name
          <input
            className={styles.input}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={100}
            placeholder="Your display name"
          />
        </label>

        <label className={styles.label}>
          Bio
          <textarea
            className={styles.textarea}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={500}
            placeholder="Tell people about yourself"
            rows={3}
          />
        </label>

        {status && (
          <p className={status.type === "error" ? styles.error : styles.success} role="alert">
            {status.msg}
          </p>
        )}

        <button type="submit" className={styles.btn} disabled={saving || uploading}>
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </section>
  );
}
