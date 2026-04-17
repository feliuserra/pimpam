import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

import MessageThread from "./MessageThread";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ userId: "42" })),
    useNavigate: vi.fn(() => vi.fn()),
  };
});

const mockUseAuth = vi.fn();
vi.mock("../contexts/AuthContext", () => ({
  useAuth: (...args) => mockUseAuth(...args),
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

vi.mock("../api/messages", () => ({
  getConversation: vi.fn(),
  getInbox: vi.fn(),
  markRead: vi.fn(),
  send: vi.fn(),
}));

vi.mock("../crypto/encrypt", () => ({
  encryptMessage: vi.fn(),
}));

vi.mock("../crypto/decrypt", () => ({
  decryptMessage: vi.fn(),
}));

import * as messagesApi from "../api/messages";
import { encryptMessage } from "../crypto/encrypt";

const defaultAuth = {
  user: { id: 1, username: "testuser", e2ee_public_key: "my-pub-key", e2ee_key_fingerprint: "aabbccdd" },
  updateUser: vi.fn(),
  isNewDevice: false,
  dismissNewDevice: vi.fn(),
  e2eeError: false,
  retryE2eeSetup: vi.fn(),
};

describe("MessageThread", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue(defaultAuth);
    messagesApi.markRead.mockResolvedValue({});
    messagesApi.getInbox.mockResolvedValue({ data: [] });
  });

  it("shows spinner while loading", () => {
    messagesApi.getConversation.mockReturnValue(new Promise(() => {}));
    render(<MessageThread />);
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
  });

  it("renders messages from API (reversed for display)", async () => {
    messagesApi.getConversation.mockResolvedValue({
      data: [
        { id: 2, sender_id: 42, sender_username: "alice", ciphertext: "Second msg", encrypted_key: "", created_at: "2026-03-25T10:01:00Z", is_read: false },
        { id: 1, sender_id: 1, sender_username: "testuser", ciphertext: "First msg", encrypted_key: "", created_at: "2026-03-25T10:00:00Z", is_read: true },
      ],
    });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText("First msg")).toBeInTheDocument();
    });

    expect(screen.getByText("Second msg")).toBeInTheDocument();
  });

  it("calls markRead on mount", async () => {
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(messagesApi.markRead).toHaveBeenCalledWith(42);
    });
  });

  it("shows waiting message when recipient has no key", async () => {
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText(/waiting for recipient/i)).toBeInTheDocument();
    });
  });

  it("shows e2ee error banner when e2eeError is true", async () => {
    mockUseAuth.mockReturnValue({ ...defaultAuth, e2eeError: true });
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText(/encryption setup failed/i)).toBeInTheDocument();
    });
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("retry button calls retryE2eeSetup", async () => {
    const retryFn = vi.fn();
    mockUseAuth.mockReturnValue({ ...defaultAuth, e2eeError: true, retryE2eeSetup: retryFn });
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Retry"));
    expect(retryFn).toHaveBeenCalled();
  });

  it("shows Back button", async () => {
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText(/back/i)).toBeInTheDocument();
    });
  });
});
