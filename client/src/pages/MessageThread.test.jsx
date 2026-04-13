import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ userId: "42" })),
    useNavigate: vi.fn(() => vi.fn()),
  };
});

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser" },
    updateUser: vi.fn(),
    deviceId: 7,
    isNewDevice: false,
    dismissNewDevice: vi.fn(),
  })),
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

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => vi.fn()),
}));

vi.mock("../api/messages", () => ({
  getConversation: vi.fn(),
  getInbox: vi.fn(),
  getSingleMessage: vi.fn(),
  markRead: vi.fn(),
  send: vi.fn(),
  deleteMessage: vi.fn(),
}));

vi.mock("../api/users", () => ({
  getUser: vi.fn(),
}));

vi.mock("../api/devices", () => ({
  getUserDeviceKeys: vi.fn(),
  getMyDevices: vi.fn(),
}));

vi.mock("../crypto/encrypt", () => ({
  encryptMessage: vi.fn(),
}));

vi.mock("../crypto/tryDecrypt", () => ({
  tryDecrypt: vi.fn((msg) => Promise.resolve({ ...msg, decryptedText: msg.ciphertext })),
}));

vi.mock("../crypto/verification", () => ({
  getVerification: vi.fn(() => Promise.resolve(null)),
  saveVerification: vi.fn(),
  clearVerification: vi.fn(),
}));

vi.mock("../crypto/fingerprint", () => ({
  computeFingerprint: vi.fn(() => Promise.resolve("abcd1234")),
  computeSafetyNumber: vi.fn(() => "12345 67890 12345 67890 12345 67890 12345 67890 12345 67890 12345 67890"),
}));

vi.mock("../components/SafetyNumberModal", () => ({
  default: () => null,
}));

import MessageThread from "./MessageThread";
import * as messagesApi from "../api/messages";
import * as usersApi from "../api/users";
import * as devicesApi from "../api/devices";

describe("MessageThread", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    messagesApi.markRead.mockResolvedValue({});
    messagesApi.getInbox.mockResolvedValue({ data: [] });
    devicesApi.getUserDeviceKeys.mockResolvedValue({ data: [] });
    devicesApi.getMyDevices.mockResolvedValue({ data: [] });
  });

  it("shows spinner while loading", () => {
    messagesApi.getConversation.mockReturnValue(new Promise(() => {}));
    render(<MessageThread />);
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
  });

  it("renders messages from API (reversed for display)", async () => {
    messagesApi.getConversation.mockResolvedValue({
      data: [
        { id: 2, sender_id: 42, sender_username: "alice", ciphertext: "Second msg", created_at: "2026-03-25T10:01:00Z", is_read: false },
        { id: 1, sender_id: 1, sender_username: "testuser", ciphertext: "First msg", created_at: "2026-03-25T10:00:00Z", is_read: true },
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

  it("sending a message calls API with device_keys", async () => {
    messagesApi.getConversation.mockResolvedValue({ data: [] });
    messagesApi.send.mockResolvedValue({
      data: { id: 100, sender_id: 1, ciphertext: "Hello!", created_at: "2026-03-25T10:05:00Z", is_read: false },
    });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Write a message...")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText("Write a message...");
    fireEvent.change(input, { target: { value: "Hello!" } });
    fireEvent.submit(input.closest("form"));

    await waitFor(() => {
      expect(messagesApi.send).toHaveBeenCalledWith({
        recipient_id: 42,
        ciphertext: "Hello!",
        device_keys: [],
      });
    });
  });

  it("shows Back button", async () => {
    messagesApi.getConversation.mockResolvedValue({ data: [] });

    render(<MessageThread />);

    await waitFor(() => {
      expect(screen.getByText(/back/i)).toBeInTheDocument();
    });
  });
});
