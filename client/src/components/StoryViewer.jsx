import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import CloseIcon from "./ui/icons/CloseIcon";
import styles from "./StoryViewer.module.css";

export default function StoryViewer({ group, onClose }) {
  const [index, setIndex] = useState(0);
  const story = group.items[index];

  const goNext = useCallback(() => {
    if (index < group.items.length - 1) {
      setIndex((i) => i + 1);
    } else {
      onClose();
    }
  }, [index, group.items.length, onClose]);

  const goPrev = useCallback(() => {
    if (index > 0) setIndex((i) => i - 1);
  }, [index]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") goNext();
      if (e.key === "ArrowLeft") goPrev();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose, goNext, goPrev]);

  if (!story) return null;

  return createPortal(
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Story viewer">
      <button className={styles.close} onClick={onClose} aria-label="Close">
        <CloseIcon size={28} />
      </button>

      <div className={styles.content}>
        <button
          className={`${styles.nav} ${styles.navLeft}`}
          onClick={goPrev}
          disabled={index === 0}
          aria-label="Previous story"
        />
        <button
          className={`${styles.nav} ${styles.navRight}`}
          onClick={goNext}
          aria-label="Next story"
        />

        <img
          className={styles.image}
          src={story.image_url}
          alt={story.caption || "Story"}
        />

        {story.caption && (
          <div className={styles.caption}>{story.caption}</div>
        )}

        <div className={styles.author}>
          {group.author?.display_name || group.author?.username}
        </div>
      </div>

      <div className={styles.dots}>
        {group.items.map((_, i) => (
          <span
            key={i}
            className={`${styles.dot} ${i === index ? styles.dotActive : ""}`}
          />
        ))}
      </div>
    </div>,
    document.body,
  );
}
