import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import NewMessageModal from "./NewMessageModal";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser", e2ee_public_key: "my-pub-key" },
    updateUser: vi.fn(),
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

vi.mock("../api/users", () => ({
  getUser: vi.fn(),
}));

vi.mock("../api/messages", () => ({
  send: vi.fn(),
}));

vi.mock("../crypto/encrypt", () => ({
  encryptMessage: vi.fn(),
}));

import * as usersApi from "../api/users";
import * as messagesApi from "../api/messages";
import { encryptMessage } from "../crypto/encrypt";

function renderModal(props = {}) {
  return render(
    <BrowserRouter>
      <NewMessageModal open={true} onClose={vi.fn()} {...props} />
    </BrowserRouter>,
  );
}

describe("NewMessageModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders username input and message textarea", () => {
    renderModal();
    expect(screen.getByPlaceholderText("@username")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Encrypted message...")).toBeInTheDocument();
  });

  it("shows encryption note", () => {
    renderModal();
    expect(screen.getByText(/end-to-end encrypted/i)).toBeInTheDocument();
  });

  it("sends encrypted message when recipient has key", async () => {
    usersApi.getUser.mockResolvedValue({
      data: { id: 99, username: "recipient", e2ee_public_key: "recipient-pub-key" },
    });
    encryptMessage.mockResolvedValue({
      ciphertext: "encrypted-ct",
      encryptedKey: "wrapped-key",
      senderEncryptedKey: "sender-wrapped",
    });
    messagesApi.send.mockResolvedValue({});
    const onClose = vi.fn();

    renderModal({ onClose });

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "recipient" },
    });
    fireEvent.change(screen.getByPlaceholderText("Encrypted message..."), {
      target: { value: "Hi there!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(encryptMessage).toHaveBeenCalledWith("Hi there!", "recipient-pub-key", "my-pub-key");
    });

    await waitFor(() => {
      expect(messagesApi.send).toHaveBeenCalledWith({
        recipient_id: 99,
        ciphertext: "encrypted-ct",
        encrypted_key: "wrapped-key",
        sender_encrypted_key: "sender-wrapped",
      });
    });
  });

  it("shows error when recipient has no encryption key", async () => {
    usersApi.getUser.mockResolvedValue({
      data: { id: 99, username: "recipient", e2ee_public_key: null },
    });

    renderModal();

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "recipient" },
    });
    fireEvent.change(screen.getByPlaceholderText("Encrypted message..."), {
      target: { value: "Hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/hasn't set up encryption/i);
    });
    expect(messagesApi.send).not.toHaveBeenCalled();
  });

  it("shows error on user not found", async () => {
    usersApi.getUser.mockRejectedValue({ response: { status: 404 } });

    renderModal();

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "nobody" },
    });
    fireEvent.change(screen.getByPlaceholderText("Encrypted message..."), {
      target: { value: "Hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("User not found");
    });
  });
});
