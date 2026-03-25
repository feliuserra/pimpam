import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// Define mock functions before vi.mock calls
const mockAddToast = vi.fn();
const mockUpdateUser = vi.fn();
const mockUser = { id: 1, username: "testuser" };
const wsHandlers = new Map();

vi.mock("../api/notifications", () => ({
  getUnreadCount: vi.fn(),
}));

vi.mock("../api/messages", () => ({
  getInbox: vi.fn(),
}));

vi.mock("./AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: mockUser, updateUser: mockUpdateUser })),
}));

vi.mock("./ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("./WSContext", () => ({
  useWS: vi.fn((eventType, handler) => {
    wsHandlers.set(eventType, handler);
  }),
}));

import { NotificationProvider, useNotifications } from "./NotificationContext";
import * as notificationsApi from "../api/notifications";
import * as messagesApi from "../api/messages";
import { useAuth } from "./AuthContext";

describe("NotificationContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    wsHandlers.clear();

    useAuth.mockReturnValue({ user: mockUser, updateUser: mockUpdateUser });

    notificationsApi.getUnreadCount.mockResolvedValue({
      data: { count: 5 },
    });
    messagesApi.getInbox.mockResolvedValue({
      data: [
        { unread_count: 2 },
        { unread_count: 3 },
      ],
    });
  });

  const wrapper = ({ children }) => (
    <NotificationProvider>{children}</NotificationProvider>
  );

  it("throws when used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      renderHook(() => useNotifications());
    }).toThrow("useNotifications must be used within NotificationProvider");

    spy.mockRestore();
  });

  it("fetches initial counts on mount when user exists", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadNotifications).toBe(5);
    });

    expect(result.current.unreadMessages).toBe(5); // 2 + 3
    expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
    expect(messagesApi.getInbox).toHaveBeenCalled();
  });

  it("does not fetch counts when user is null", async () => {
    useAuth.mockReturnValue({ user: null, updateUser: mockUpdateUser });

    renderHook(() => useNotifications(), { wrapper });

    // Give it time to potentially fetch
    await new Promise((r) => setTimeout(r, 50));

    expect(notificationsApi.getUnreadCount).not.toHaveBeenCalled();
    expect(messagesApi.getInbox).not.toHaveBeenCalled();
  });

  it("decrementNotifications reduces count", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadNotifications).toBe(5);
    });

    act(() => {
      result.current.decrementNotifications(2);
    });

    expect(result.current.unreadNotifications).toBe(3);
  });

  it("decrementNotifications does not go below zero", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadNotifications).toBe(5);
    });

    act(() => {
      result.current.decrementNotifications(100);
    });

    expect(result.current.unreadNotifications).toBe(0);
  });

  it("decrementMessages reduces count", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadMessages).toBe(5);
    });

    act(() => {
      result.current.decrementMessages(1);
    });

    expect(result.current.unreadMessages).toBe(4);
  });

  it("decrementMessages does not go below zero", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadMessages).toBe(5);
    });

    act(() => {
      result.current.decrementMessages(100);
    });

    expect(result.current.unreadMessages).toBe(0);
  });

  it("clearNotifications sets count to zero", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadNotifications).toBe(5);
    });

    act(() => {
      result.current.clearNotifications();
    });

    expect(result.current.unreadNotifications).toBe(0);
  });

  it("refetch triggers a new count fetch", async () => {
    const { result } = renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(result.current.unreadNotifications).toBe(5);
    });

    // Update mock to return different values
    notificationsApi.getUnreadCount.mockResolvedValue({
      data: { count: 10 },
    });
    messagesApi.getInbox.mockResolvedValue({
      data: [{ unread_count: 7 }],
    });

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.unreadNotifications).toBe(10);
    expect(result.current.unreadMessages).toBe(7);
  });

  it("notification WS event triggers refetch and toast", async () => {
    renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
    });

    // Simulate WS notification event
    const notifHandler = wsHandlers.get("notification");
    expect(notifHandler).toBeDefined();

    notificationsApi.getUnreadCount.mockResolvedValue({
      data: { count: 6 },
    });

    await act(async () => {
      notifHandler({ message: "New follower!" });
    });

    expect(mockAddToast).toHaveBeenCalledWith("New follower!", "info");
  });

  it("notification WS event without message does not show toast", async () => {
    renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
    });

    const notifHandler = wsHandlers.get("notification");

    await act(async () => {
      notifHandler({});
    });

    expect(mockAddToast).not.toHaveBeenCalled();
  });

  it("new_message WS event triggers refetch", async () => {
    renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(messagesApi.getInbox).toHaveBeenCalled();
    });

    const msgHandler = wsHandlers.get("new_message");
    expect(msgHandler).toBeDefined();

    messagesApi.getInbox.mockResolvedValue({
      data: [{ unread_count: 10 }],
    });

    await act(async () => {
      msgHandler();
    });

    // Should have re-fetched
    expect(messagesApi.getInbox).toHaveBeenCalledTimes(2);
  });

  it("karma_update WS event calls updateUser", async () => {
    renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
    });

    const karmaHandler = wsHandlers.get("karma_update");
    expect(karmaHandler).toBeDefined();

    act(() => {
      karmaHandler({ karma: 42 });
    });

    expect(mockUpdateUser).toHaveBeenCalledWith({ karma: 42 });
  });

  it("karma_update without karma field does not call updateUser", async () => {
    renderHook(() => useNotifications(), { wrapper });

    await waitFor(() => {
      expect(notificationsApi.getUnreadCount).toHaveBeenCalled();
    });

    const karmaHandler = wsHandlers.get("karma_update");

    act(() => {
      karmaHandler({});
    });

    expect(mockUpdateUser).not.toHaveBeenCalled();
  });

  it("handles fetch errors silently", async () => {
    notificationsApi.getUnreadCount.mockRejectedValue(new Error("fail"));
    messagesApi.getInbox.mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useNotifications(), { wrapper });

    // Should not throw, counts stay at 0
    await new Promise((r) => setTimeout(r, 50));

    expect(result.current.unreadNotifications).toBe(0);
    expect(result.current.unreadMessages).toBe(0);
  });
});
