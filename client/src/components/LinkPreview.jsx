import { useState, useEffect } from "react";
import Skeleton from "./ui/Skeleton";
import * as postsApi from "../api/posts";
import styles from "./LinkPreview.module.css";

export default function LinkPreview({ url }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    postsApi.getLinkPreview(url)
      .then((res) => {
        if (!cancelled && (res.data.title || res.data.image)) {
          setPreview(res.data);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [url]);

  if (!url || (!loading && !preview)) return null;

  if (loading) {
    return (
      <div className={styles.card}>
        <Skeleton width="100%" height="0.85rem" />
        <Skeleton width="70%" height="0.75rem" />
      </div>
    );
  }

  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className={styles.card}>
      {preview.image && (
        <img
          src={preview.image}
          alt=""
          className={styles.image}
          loading="lazy"
          onError={(e) => { e.target.style.display = "none"; }}
        />
      )}
      <div className={styles.body}>
        {preview.site_name && (
          <span className={styles.site}>{preview.site_name}</span>
        )}
        {preview.title && (
          <span className={styles.title}>{preview.title}</span>
        )}
        {preview.description && (
          <span className={styles.description}>{preview.description}</span>
        )}
      </div>
    </a>
  );
}
