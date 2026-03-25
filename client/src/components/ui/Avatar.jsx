import { useState } from "react";
import styles from "./Avatar.module.css";

export default function Avatar({
  src,
  alt,
  size = 40,
  hasStory,
  unseenStory,
  showPlus,
  className = "",
}) {
  const [imgError, setImgError] = useState(false);

  const initials = alt
    ? alt
        .replace(/^@/, "")
        .slice(0, 2)
        .toUpperCase()
    : "?";

  const showImg = src && !imgError;

  return (
    <div
      className={`${styles.wrapper} ${hasStory ? (unseenStory ? styles.unseen : styles.seen) : ""} ${className}`}
      style={{ "--avatar-size": `${size}px`, width: size, height: size }}
    >
      {showImg ? (
        <img
          className={styles.img}
          src={src}
          alt={alt}
          width={size}
          height={size}
          style={{ width: size, height: size }}
          onError={() => setImgError(true)}
        />
      ) : (
        <span className={styles.fallback} style={{ width: size, height: size }}>{initials}</span>
      )}
      {showPlus && <span className={styles.plus}>+</span>}
    </div>
  );
}
