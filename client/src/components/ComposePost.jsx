import { useCallback, useEffect, useRef, useState } from "react";
import { create } from "../api/posts";
import { listJoined } from "../api/communities";
import { upload } from "../api/media";
import { useToast } from "../contexts/ToastContext";
import Modal from "./ui/Modal";
import Button from "./ui/Button";
import ImageIcon from "./ui/icons/ImageIcon";
import CloseIcon from "./ui/icons/CloseIcon";
import styles from "./ComposePost.module.css";

export default function ComposePost({ open, onClose, onCreated }) {
  const { addToast } = useToast();
  const fileRef = useRef(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [communityId, setCommunityId] = useState("");
  const [communities, setCommunities] = useState([]);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchCommunities = useCallback(async () => {
    try {
      const { data } = await listJoined();
      setCommunities(data);
    } catch {
      // non-critical
    }
  }, []);

  useEffect(() => {
    if (open) fetchCommunities();
  }, [open, fetchCommunities]);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImageFile(f);
    setImagePreview(URL.createObjectURL(f));
  };

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const reset = () => {
    setTitle("");
    setContent("");
    setUrl("");
    setCommunityId("");
    removeImage();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    try {
      let image_url = null;
      if (imageFile) {
        const { data: media } = await upload(imageFile, "post");
        image_url = media.url;
      }
      const body = {
        title: title.trim(),
        content: content.trim() || null,
        url: url.trim() || null,
        image_url,
        community_id: communityId ? Number(communityId) : null,
      };
      const { data: post } = await create(body);
      addToast("Post created!", "success");
      reset();
      onClose();
      onCreated?.(post);
    } catch (err) {
      const detail = err.response?.data?.detail;
      addToast(typeof detail === "string" ? detail : "Failed to create post.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="New post">
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Title *"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className={styles.titleInput}
          required
        />

        <textarea
          placeholder="What's on your mind?"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className={styles.textarea}
          rows={4}
        />

        <input
          type="url"
          placeholder="Link (optional)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          className={styles.input}
        />

        {communities.length > 0 && (
          <select
            value={communityId}
            onChange={(e) => setCommunityId(e.target.value)}
            className={styles.input}
            aria-label="Community"
          >
            <option value="">No community (personal)</option>
            {communities.map((c) => (
              <option key={c.id} value={c.id}>
                c/{c.name}
              </option>
            ))}
          </select>
        )}

        {imagePreview ? (
          <div className={styles.imageWrap}>
            <img src={imagePreview} alt="Upload preview" className={styles.imagePreview} />
            <button
              type="button"
              className={styles.removeImage}
              onClick={removeImage}
              aria-label="Remove image"
            >
              <CloseIcon size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            className={styles.addImage}
            onClick={() => fileRef.current?.click()}
          >
            <ImageIcon size={18} />
            <span>Add image</span>
          </button>
        )}

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleFile}
          hidden
        />

        <div className={styles.actions}>
          <Button variant="ghost" type="button" onClick={handleClose}>Cancel</Button>
          <Button type="submit" loading={loading} disabled={!title.trim()}>Post</Button>
        </div>
      </form>
    </Modal>
  );
}
