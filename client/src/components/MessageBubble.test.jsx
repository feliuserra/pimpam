import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageBubble from "./MessageBubble";

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
  })),
}));

const baseMessage = {
  id: 1,
  sender_id: 1,
  ciphertext: "Hello there!",
  created_at: "2026-03-25T10:00:00Z",
  is_read: false,
};

describe("MessageBubble", () => {
  it("renders message text (ciphertext field)", () => {
    render(<MessageBubble message={baseMessage} isOwn={false} />);
    expect(screen.getByText("Hello there!")).toBeInTheDocument();
  });

  it("own messages have 'own' styling class", () => {
    const { container } = render(<MessageBubble message={baseMessage} isOwn={true} />);
    const row = container.querySelector(".row");
    expect(row).toHaveClass("own");
  });

  it("their messages have 'theirs' styling class", () => {
    const { container } = render(
      <MessageBubble message={{ ...baseMessage, sender_id: 42 }} isOwn={false} />,
    );
    const row = container.querySelector(".row");
    expect(row).toHaveClass("theirs");
  });

  it("shows read checkmark for own read messages", () => {
    const readMessage = { ...baseMessage, is_read: true };
    const { container } = render(<MessageBubble message={readMessage} isOwn={true} />);
    const readMark = container.querySelector(".read");
    expect(readMark).toBeInTheDocument();
  });

  it("does not show read checkmark for own unread messages", () => {
    const { container } = render(<MessageBubble message={baseMessage} isOwn={true} />);
    const readMark = container.querySelector(".read");
    expect(readMark).not.toBeInTheDocument();
  });

  it("does not show read checkmark for their messages even if read", () => {
    const readMessage = { ...baseMessage, sender_id: 42, is_read: true };
    const { container } = render(<MessageBubble message={readMessage} isOwn={false} />);
    const readMark = container.querySelector(".read");
    expect(readMark).not.toBeInTheDocument();
  });
});
