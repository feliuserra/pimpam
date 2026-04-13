import styles from "./DateSeparator.module.css";

function formatDateLabel(dateStr) {
  const date = new Date(dateStr);
  const now = new Date();

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const msgDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (msgDay.getTime() === today.getTime()) return "Today";
  if (msgDay.getTime() === yesterday.getTime()) return "Yesterday";
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: msgDay.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  }).format(date);
}

export default function DateSeparator({ date }) {
  return (
    <div className={styles.separator} aria-label={`Messages from ${formatDateLabel(date)}`}>
      <span className={styles.label}>{formatDateLabel(date)}</span>
    </div>
  );
}
