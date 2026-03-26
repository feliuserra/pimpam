import { useRef, useState } from "react";
import { create } from "../api/stories";
import { upload } from "../api/media";
import { useToast } from "../contexts/ToastContext";
import Modal from "./ui/Modal";
import Button from "./ui/Button";
import ImageIcon from "./ui/icons/ImageIcon";
import styles from "./StoryCompose.module.css";

const DURATION_OPTIONS = [
  { label: "12h", value: 12 },
  { label: "24h", value: 24 },
  { label: "48h", value: 48 },
  { label: "7 days", value: 168 },
];

export default function StoryCompose({ open, onClose }) {
  const { addToast } = useToast();
  const fileRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [file, setFile] = useState(null);
  const [caption, setCaption] = useState("");
  const [duration, setDuration] = useState(24);
  const [loading, setLoading] = useState(false);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const reset = () => {
    setPreview(null);
    setFile(null);
    setCaption("");
    setDuration(24);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const { data: media } = await upload(file, "post_image");
      await create({ image_url: media.url, caption: caption || null, duration_hours: duration });
      addToast("Story posted!", "success");
      reset();
      onClose();
    } catch {
      addToast("Failed to post story.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="New story">
      {!preview ? (
        <div className={styles.picker}>
          <button
            className={styles.pickBtn}
            onClick={() => fileRef.current?.click()}
            aria-label="Choose image"
          >
            <ImageIcon size={32} />
            <span>Choose an image</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            onChange={handleFile}
            hidden
          />
        </div>
      ) : (
        <div className={styles.form}>
          <img src={preview} alt="Preview" className={styles.preview} />

          <label htmlFor="story-caption" className={styles.label}>
            Caption (optional)
          </label>
          <input
            id="story-caption"
            type="text"
            maxLength={200}
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Add a caption..."
            className={styles.input}
          />
          <span className={styles.charCount}>{caption.length}/200</span>

          <label className={styles.label}>Duration</label>
          <div className={styles.durations}>
            {DURATION_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`${styles.durBtn} ${duration === opt.value ? styles.durActive : ""}`}
                onClick={() => setDuration(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className={styles.actions}>
            <Button variant="ghost" onClick={handleClose}>Cancel</Button>
            <Button loading={loading} onClick={handleSubmit}>Post story</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
