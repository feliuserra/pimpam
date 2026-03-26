import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "./ui/Modal";
import * as communitiesApi from "../api/communities";
import styles from "./CreateCommunityModal.module.css";

export default function CreateCommunityModal({ open, onClose }) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      const res = await communitiesApi.create({
        name: name.trim(),
        description: description.trim() || null,
      });
      onClose();
      navigate(`/c/${res.data.name}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create community");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Create Community">
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label}>
          Name
          <input
            className={styles.input}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. photography"
            minLength={3}
            maxLength={100}
            required
          />
          <span className={styles.hint}>
            Letters, numbers, hyphens, underscores. 3-100 chars.
          </span>
        </label>

        <label className={styles.label}>
          Description (optional)
          <textarea
            className={styles.textarea}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this community about?"
            rows={3}
          />
        </label>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button
          type="submit"
          className={styles.submitBtn}
          disabled={saving || name.trim().length < 3}
        >
          {saving ? "Creating..." : "Create"}
        </button>
      </form>
    </Modal>
  );
}
