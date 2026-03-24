import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getInbox } from "../api/messages";
import { getUnreadCount } from "../api/notifications";
import { useAuth } from "./AuthContext";
import { useWS } from "./WSContext";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { user } = useAuth();
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [unreadMessages, setUnreadMessages] = useState(0);

  const fetchCounts = useCallback(async () => {
    if (!user) return;
    try {
      const [notifRes, msgRes] = await Promise.all([
        getUnreadCount(),
        getInbox(),
      ]);
      setUnreadNotifications(notifRes.data.count);
      const totalUnread = msgRes.data.reduce(
        (sum, c) => sum + (c.unread_count || 0),
        0,
      );
      setUnreadMessages(totalUnread);
    } catch {
      // silently fail — badges just won't update
    }
  }, [user]);

  useEffect(() => {
    fetchCounts();
  }, [fetchCounts]);

  useWS(
    "notification",
    useCallback(() => {
      setUnreadNotifications((n) => n + 1);
    }, []),
  );

  useWS(
    "new_message",
    useCallback(() => {
      setUnreadMessages((n) => n + 1);
    }, []),
  );

  const decrementNotifications = useCallback((count = 1) => {
    setUnreadNotifications((n) => Math.max(0, n - count));
  }, []);

  const decrementMessages = useCallback((count = 1) => {
    setUnreadMessages((n) => Math.max(0, n - count));
  }, []);

  const clearNotifications = useCallback(() => {
    setUnreadNotifications(0);
  }, []);

  const value = useMemo(
    () => ({
      unreadNotifications,
      unreadMessages,
      decrementNotifications,
      decrementMessages,
      clearNotifications,
      refetch: fetchCounts,
    }),
    [
      unreadNotifications,
      unreadMessages,
      decrementNotifications,
      decrementMessages,
      clearNotifications,
      fetchCounts,
    ],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx)
    throw new Error("useNotifications must be used within NotificationProvider");
  return ctx;
}
