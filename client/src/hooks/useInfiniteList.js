import { useCallback, useEffect, useRef, useState } from "react";

export function useInfiniteList(fetchFn) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const sentinelRef = useRef(null);
  const cursorRef = useRef(null);
  const fetchingRef = useRef(false);
  const initialLoadDone = useRef(false);

  const loadMore = useCallback(async () => {
    if (fetchingRef.current || !hasMore) return;
    fetchingRef.current = true;
    setLoading(true);
    try {
      const { data } = await fetchFn(cursorRef.current);
      if (!data || data.length === 0) {
        setHasMore(false);
      } else {
        setItems((prev) => [...prev, ...data]);
        cursorRef.current = data[data.length - 1].id;
      }
    } catch {
      // stop loading on error — user can scroll again to retry
      setHasMore(false);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  }, [fetchFn, hasMore]);

  // Explicit initial load — don't rely solely on IntersectionObserver
  useEffect(() => {
    if (initialLoadDone.current) return;
    initialLoadDone.current = true;
    loadMore();
  }, [loadMore]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) loadMore();
      },
      { rootMargin: "200px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [loadMore]);

  const refresh = useCallback(async () => {
    cursorRef.current = null;
    setHasMore(true);
    fetchingRef.current = true; // block loadMore from running concurrently
    initialLoadDone.current = true; // prevent initial load from re-firing
    setItems([]);
    setLoading(true);
    try {
      const { data } = await fetchFn(null);
      if (!data || data.length === 0) {
        setHasMore(false);
      } else {
        setItems(data);
        cursorRef.current = data[data.length - 1].id;
      }
    } catch {
      setHasMore(false);
    } finally {
      setLoading(false);
      fetchingRef.current = false;
    }
  }, [fetchFn]);

  return { items, setItems, loading, hasMore, sentinelRef, refresh };
}
