import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Messages from "./Messages";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" }, updateUser: vi.fn() })),
}));

vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));

vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
    clearNotifications: vi.fn(),
    decrementNotifications: vi.fn(),
    refetch: vi.fn(),
  })),
}));

vi.mock("../api/messages", () => ({
  getInbox: vi.fn(),
}));

vi.mock("../api/users", () => ({
  getFollowing: vi.fn(() => Promise.resolve({ data: [] })),
}));

vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));

vi.mock("../components/NewMessageModal", () => ({
  default: ({ open, onClose }) =>
    open ? (
      <div role="dialog" aria-label="New message">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

import * as messagesApi from "../api/messages";

function renderMessages() {
  return render(
    <BrowserRouter>
      <Messages />
    </BrowserRouter>,
  );
}

describe("Messages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows spinner while loading", () => {
    messagesApi.getInbox.mockReturnValue(new Promise(() => {}));
    renderMessages();
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
  });

  it("renders conversation list from API", async () => {
    messagesApi.getInbox.mockResolvedValue({
      data: [
        {
          other_user_id: 2,
          other_username: "alice",
          other_avatar_url: null,
          last_message_at: "2026-03-25T10:00:00Z",
          unread_count: 3,
        },
        {
          other_user_id: 3,
          other_username: "bob",
          other_avatar_url: null,
          last_message_at: "2026-03-24T09:00:00Z",
          unread_count: 0,
        },
      ],
    });

    renderMessages();

    await waitFor(() => {
      expect(screen.getByText("@alice")).toBeInTheDocument();
    });

    expect(screen.getByText("@bob")).toBeInTheDocument();
    expect(screen.getByText("3 unread")).toBeInTheDocument();
  });

  it("shows empty state when no conversations", async () => {
    messagesApi.getInbox.mockResolvedValue({ data: [] });

    renderMessages();

    await waitFor(() => {
      expect(screen.getByText("No messages yet.")).toBeInTheDocument();
    });

    expect(screen.getByText("Start a conversation")).toBeInTheDocument();
  });

  it("'Start a conversation' button opens compose modal", async () => {
    messagesApi.getInbox.mockResolvedValue({ data: [] });

    renderMessages();

    await waitFor(() => {
      expect(screen.getByText("Start a conversation")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Start a conversation"));

    await waitFor(() => {
      expect(screen.getByRole("dialog", { name: /new message/i })).toBeInTheDocument();
    });
  });
});
