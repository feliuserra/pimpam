import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import CloseIcon from "./ui/icons/CloseIcon";
import styles from "./StoryViewer.module.css";

const STORY_DURATION = 6000; // 6 seconds per story

export default function StoryViewer({ group, onClose }) {
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const rafRef = useRef(null);
  const startRef = useRef(null);
  const pausedAtRef = useRef(0);
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

  // Reset progress when story changes
  useEffect(() => {
    setProgress(0);
    startRef.current = null;
    pausedAtRef.current = 0;
  }, [index]);

  // Auto-advance timer with smooth progress
  useEffect(() => {
    if (paused) {
      pausedAtRef.current = progress;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      return;
    }

    const elapsed = pausedAtRef.current * STORY_DURATION;
    startRef.current = performance.now() - elapsed;

    const tick = (now) => {
      const dt = now - startRef.current;
      const pct = Math.min(dt / STORY_DURATION, 1);
      setProgress(pct);
      if (pct < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        goNext();
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [index, paused, goNext]);

  // Keyboard controls
  useEffect(() => {
    const handler = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") goNext();
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === " ") {
        e.preventDefault();
        setPaused((p) => !p);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose, goNext, goPrev]);

  if (!story) return null;

  return createPortal(
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Story viewer">
      {/* Progress bars */}
      <div className={styles.progressRow}>
        {group.items.map((_, i) => (
          <div key={i} className={styles.progressTrack}>
            <div
              className={styles.progressFill}
              style={{
                width:
                  i < index ? "100%" : i === index ? `${progress * 100}%` : "0%",
              }}
            />
          </div>
        ))}
      </div>

      <div className={styles.topBar}>
        <button
          className={styles.authorBtn}
          onClick={() => { onClose(); navigate(`/u/${group.author?.username}`); }}
        >
          {group.author?.display_name || group.author?.username}
        </button>
        <button className={styles.close} onClick={onClose} aria-label="Close">
          <CloseIcon size={24} />
        </button>
      </div>

      <div
        className={styles.content}
        onPointerDown={() => setPaused(true)}
        onPointerUp={() => setPaused(false)}
        onPointerLeave={() => setPaused(false)}
      >
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
      </div>
    </div>,
    document.body,
  );
}
