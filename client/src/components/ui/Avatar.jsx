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
  const initials = alt
    ? alt
        .replace(/^@/, "")
        .slice(0, 2)
        .toUpperCase()
    : "?";

  return (
    <div
      className={`${styles.wrapper} ${hasStory ? (unseenStory ? styles.unseen : styles.seen) : ""} ${className}`}
      style={{ "--avatar-size": `${size}px` }}
    >
      {src ? (
        <img
          className={styles.img}
          src={src}
          alt={alt}
          width={size}
          height={size}
          loading="lazy"
        />
      ) : (
        <span className={styles.fallback}>{initials}</span>
      )}
      {showPlus && <span className={styles.plus}>+</span>}
    </div>
  );
}
