import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getInbox } from "../api/messages";
import { getUnreadCount } from "../api/notifications";
import { useAuth } from "./AuthContext";
import { useWS } from "./WSContext";
import { useToast } from "./ToastContext";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { user, updateUser } = useAuth();
  const { addToast } = useToast();
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
    useCallback(
      (data) => {
        // Re-fetch server count instead of blindly incrementing
        fetchCounts();
        if (data?.message) {
          addToast(data.message, "info");
        }
      },
      [addToast, fetchCounts],
    ),
  );

  useWS(
    "new_message",
    useCallback(() => {
      // Re-fetch server count instead of blindly incrementing
      fetchCounts();
    }, [fetchCounts]),
  );

  useWS(
    "karma_update",
    useCallback(
      (data) => {
        if (data?.karma != null) {
          updateUser({ karma: data.karma });
        }
      },
      [updateUser],
    ),
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
