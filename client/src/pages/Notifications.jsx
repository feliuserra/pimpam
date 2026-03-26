import { useCallback, useEffect, useState } from "react";
import Header from "../components/Header";
import NotificationItem from "../components/NotificationItem";
import Spinner from "../components/ui/Spinner";
import CheckIcon from "../components/ui/icons/CheckIcon";
import { useNotifications } from "../contexts/NotificationContext";
import * as notificationsApi from "../api/notifications";
import styles from "./Notifications.module.css";

const TABS = [
  { key: null, label: "All" },
  { key: "follows", label: "Follows" },
  { key: "karma", label: "Karma" },
  { key: "comments", label: "Comments" },
  { key: "other", label: "Other" },
];

const PAGE_SIZES = [20, 50, 100];

export default function Notifications() {
  const { clearNotifications, decrementNotifications, refetch } = useNotifications();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [tab, setTab] = useState(null);
  const [pageSize, setPageSize] = useState(20);
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState(new Set());

  const load = useCallback(async (cursor = null, replace = false) => {
    setLoading(true);
    try {
      const params = { limit: pageSize };
      if (cursor) params.before_id = cursor;
      if (tab) params.type_group = tab;
      const { data } = await notificationsApi.list(params);
      if (!data || data.length === 0) {
        setHasMore(false);
        if (replace) setItems([]);
      } else {
        setItems((prev) => replace ? data : [...prev, ...data]);
        setHasMore(data.length >= pageSize);
      }
    } catch {
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }, [tab, pageSize]);

  // Reload when tab or page size changes
  useEffect(() => {
    setItems([]);
    setHasMore(true);
    setSelected(new Set());
    load(null, true);
    refetch();
  }, [load, refetch]);

  const handleLoadMore = () => {
    if (!hasMore || loading || items.length === 0) return;
    const lastId = items[items.length - 1].id;
    load(lastId);
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      clearNotifications();
    } catch { /* silent */ }
  };

  const handleRead = async (id) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      decrementNotifications();
    } catch { /* silent */ }
  };

  const handleDismiss = async (id) => {
    const item = items.find((n) => n.id === id);
    setItems((prev) => prev.filter((n) => n.id !== id));
    setSelected((prev) => { const s = new Set(prev); s.delete(id); return s; });
    if (item && !item.is_read) decrementNotifications();
    try {
      await notificationsApi.dismiss(id);
    } catch { /* silent */ }
  };

  const handleSelect = (id) => {
    setSelected((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return s;
    });
  };

  const handleSelectAll = () => {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((n) => n.id)));
    }
  };

  const handleBatchRead = async () => {
    const ids = [...selected];
    const unreadIds = ids.filter((id) => items.find((n) => n.id === id && !n.is_read));
    setItems((prev) =>
      prev.map((n) => (selected.has(n.id) ? { ...n, is_read: true } : n)),
    );
    setSelected(new Set());
    if (unreadIds.length > 0) decrementNotifications(unreadIds.length);
    try {
      await notificationsApi.markReadBatch(ids);
    } catch { /* silent */ }
  };

  const handleBatchDismiss = async () => {
    const ids = [...selected];
    const unreadCount = ids.filter((id) => items.find((n) => n.id === id && !n.is_read)).length;
    setItems((prev) => prev.filter((n) => !selected.has(n.id)));
    setSelected(new Set());
    if (unreadCount > 0) decrementNotifications(unreadCount);
    try {
      await notificationsApi.dismissBatch(ids);
    } catch { /* silent */ }
  };

  const handleDismissRead = async () => {
    const readItems = items.filter((n) => n.is_read);
    if (readItems.length === 0) return;
    const ids = readItems.map((n) => n.id);
    setItems((prev) => prev.filter((n) => !n.is_read));
    setSelected(new Set());
    try {
      await notificationsApi.dismissBatch(ids);
    } catch { /* silent */ }
  };

  const toggleSelectMode = () => {
    setSelectMode((v) => !v);
    setSelected(new Set());
  };

  const hasUnread = items.some((n) => !n.is_read);
  const hasRead = items.some((n) => n.is_read);

  return (
    <>
      <Header
        left={<span>Notifications</span>}
        right={
          <div className={styles.headerRight}>
            <button
              className={`${styles.headerBtn} ${selectMode ? styles.headerBtnActive : ""}`}
              onClick={toggleSelectMode}
              aria-label={selectMode ? "Exit select mode" : "Select notifications"}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="9 11 12 14 22 4" />
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
              </svg>
            </button>
            {hasUnread && (
              <button
                className={styles.headerBtn}
                onClick={handleMarkAllRead}
                aria-label="Mark all as read"
              >
                <CheckIcon size={18} />
              </button>
            )}
          </div>
        }
      />

      <div className={styles.container}>
        {/* Type filter tabs */}
        <nav className={styles.tabs}>
          {TABS.map((t) => (
            <button
              key={t.key || "all"}
              className={`${styles.tab} ${tab === t.key ? styles.activeTab : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Batch action bar */}
        {selectMode && (
          <div className={styles.batchBar}>
            <button className={styles.selectAllBtn} onClick={handleSelectAll}>
              {selected.size === items.length && items.length > 0 ? "Deselect all" : "Select all"}
            </button>
            {selected.size > 0 && (
              <>
                <span className={styles.selectedCount}>{selected.size} selected</span>
                <button className={styles.batchBtn} onClick={handleBatchRead}>
                  Mark read
                </button>
                <button className={`${styles.batchBtn} ${styles.batchDismiss}`} onClick={handleBatchDismiss}>
                  Dismiss
                </button>
              </>
            )}
          </div>
        )}

        {/* Notification list */}
        {loading && items.length === 0 ? (
          <div className={styles.loader}><Spinner size={24} /></div>
        ) : items.length === 0 ? (
          <p className={styles.empty}>
            {tab ? "No notifications in this category." : "No notifications yet."}
          </p>
        ) : (
          <div>
            {items.map((n) => (
              <NotificationItem
                key={n.id}
                notification={n}
                onRead={handleRead}
                onDismiss={handleDismiss}
                selected={selectMode ? selected.has(n.id) : undefined}
                onSelect={selectMode ? handleSelect : undefined}
              />
            ))}
          </div>
        )}

        {/* Footer: dismiss read + load more + page size */}
        <div className={styles.footer}>
          {hasRead && !selectMode && (
            <button className={styles.dismissReadBtn} onClick={handleDismissRead}>
              Dismiss all read
            </button>
          )}

          {hasMore && (
            <button
              className={styles.loadMoreBtn}
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? <Spinner size={16} /> : "Load more"}
            </button>
          )}

          <div className={styles.pageSizeRow}>
            <span className={styles.pageSizeLabel}>Show</span>
            {PAGE_SIZES.map((s) => (
              <button
                key={s}
                className={`${styles.pageSizeBtn} ${pageSize === s ? styles.pageSizeActive : ""}`}
                onClick={() => setPageSize(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
