import { useState } from "react";
import Modal from "./ui/Modal";
import Avatar from "./ui/Avatar";
import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";
import * as mediaApi from "../api/media";
import styles from "./EditProfileModal.module.css";

export default function EditProfileModal({ open, onClose }) {
  const { user, updateUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const res = await mediaApi.upload(file, "avatar");
      setAvatarPreview(res.data.url);
    } catch {
      setError("Failed to upload image");
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const res = await usersApi.updateMe({
        display_name: displayName || null,
        bio: bio || null,
        avatar_url: avatarPreview || null,
      });
      updateUser(res.data);
      onClose();
    } catch {
      setError("Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Edit Profile">
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.avatarSection}>
          <Avatar
            src={avatarPreview}
            alt={`@${user?.username}`}
            size={80}
          />
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

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button
          type="submit"
          className={styles.saveBtn}
          disabled={saving || uploading}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </Modal>
  );
}
