import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./InfoTooltip.module.css";

export default function InfoTooltip({ children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) close();
    };
    const handleKey = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, close]);

  return (
    <span className={styles.wrapper} ref={ref}>
      <button
        className={styles.trigger}
        onClick={() => setOpen((v) => !v)}
        aria-label="More info"
        type="button"
      >
        i
      </button>
      {open && (
        <div className={styles.popover} role="tooltip">
          {children}
        </div>
      )}
    </span>
  );
}
