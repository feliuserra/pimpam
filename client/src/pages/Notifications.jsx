import { useCallback, useEffect } from "react";
import Header from "../components/Header";
import NotificationItem from "../components/NotificationItem";
import Spinner from "../components/ui/Spinner";
import CheckIcon from "../components/ui/icons/CheckIcon";
import { useNotifications } from "../contexts/NotificationContext";
import { useInfiniteList } from "../hooks/useInfiniteList";
import * as notificationsApi from "../api/notifications";
import styles from "./Notifications.module.css";

export default function Notifications() {
  const { clearNotifications, decrementNotifications, refetch } = useNotifications();

  const fetchNotifications = useCallback(
    (cursor) => notificationsApi.list({ limit: 20, before_id: cursor }),
    [],
  );

  const { items, setItems, loading, hasMore, sentinelRef, refresh } =
    useInfiniteList(fetchNotifications);

  // Sync badge count with server and load notifications
  useEffect(() => {
    refresh();
    refetch();
  }, [refresh, refetch]);

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      clearNotifications();
    } catch {
      // silent
    }
  };

  const handleRead = async (id) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      );
      decrementNotifications();
    } catch {
      // silent
    }
  };

  const hasUnread = items.some((n) => !n.is_read);

  return (
    <>
      <Header
        left={<span>Notifications</span>}
        right={
          hasUnread ? (
            <button
              className={styles.markAll}
              onClick={handleMarkAllRead}
              aria-label="Mark all as read"
            >
              <CheckIcon size={18} />
            </button>
          ) : null
        }
      />

      <div className={styles.container}>
        {loading && items.length === 0 ? (
          <div className={styles.loader}><Spinner size={24} /></div>
        ) : items.length === 0 ? (
          <p className={styles.empty}>No notifications yet.</p>
        ) : (
          <div>
            {items.map((n) => (
              <NotificationItem
                key={n.id}
                notification={n}
                onRead={handleRead}
              />
            ))}
          </div>
        )}

        {hasMore && (
          <div ref={sentinelRef} className={styles.sentinel}>
            {loading && <Spinner size={20} />}
          </div>
        )}
      </div>
    </>
  );
}
