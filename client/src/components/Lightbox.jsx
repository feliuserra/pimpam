import { useEffect, useCallback } from "react";
import CloseIcon from "./ui/icons/CloseIcon";
import styles from "./Lightbox.module.css";

export default function Lightbox({ images, index, onClose, onIndexChange }) {
  const hasPrev = index > 0;
  const hasNext = index < images.length - 1;

  const handleKey = useCallback(
    (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && hasPrev) onIndexChange(index - 1);
      if (e.key === "ArrowRight" && hasNext) onIndexChange(index + 1);
    },
    [onClose, onIndexChange, index, hasPrev, hasNext],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [handleKey]);

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true" aria-label="Image viewer">
      <button className={styles.close} onClick={onClose} aria-label="Close">
        <CloseIcon size={24} />
      </button>

      <div className={styles.content} onClick={(e) => e.stopPropagation()}>
        {hasPrev && (
          <button className={`${styles.nav} ${styles.prev}`} onClick={() => onIndexChange(index - 1)} aria-label="Previous image">
            ‹
          </button>
        )}

        <img src={images[index].url} alt="" className={styles.image} />

        {hasNext && (
          <button className={`${styles.nav} ${styles.next}`} onClick={() => onIndexChange(index + 1)} aria-label="Next image">
            ›
          </button>
        )}
      </div>

      {images.length > 1 && (
        <div className={styles.dots}>
          {images.map((_, i) => (
            <span key={i} className={`${styles.dot} ${i === index ? styles.active : ""}`} />
          ))}
        </div>
      )}
    </div>
  );
}
