import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import NewMessageModal from "./NewMessageModal";

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

vi.mock("../api/users", () => ({
  getUser: vi.fn(),
}));

vi.mock("../api/messages", () => ({
  send: vi.fn(),
}));

vi.mock("../api/devices", () => ({
  getUserDeviceKeys: vi.fn(),
  getMyDevices: vi.fn(),
}));

vi.mock("../crypto/encrypt", () => ({
  encryptMessage: vi.fn(),
}));

import * as usersApi from "../api/users";
import * as messagesApi from "../api/messages";
import * as devicesApi from "../api/devices";
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
    expect(screen.getByPlaceholderText("Write your message...")).toBeInTheDocument();
  });

  it("shows error when recipient has no device keys", async () => {
    usersApi.getUser.mockResolvedValue({ data: { id: 99, username: "recipient" } });
    devicesApi.getUserDeviceKeys.mockResolvedValue({ data: [] });
    devicesApi.getMyDevices.mockResolvedValue({ data: [] });

    renderModal();

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "recipient" },
    });
    fireEvent.change(screen.getByPlaceholderText("Write your message..."), {
      target: { value: "Hi there!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /hasn't set up encryption/i,
      );
    });

    expect(messagesApi.send).not.toHaveBeenCalled();
  });

  it("encrypts and sends when recipient has device keys", async () => {
    usersApi.getUser.mockResolvedValue({ data: { id: 99, username: "recipient" } });
    devicesApi.getUserDeviceKeys.mockResolvedValue({
      data: [{ device_id: 5, public_key: "recip-key" }],
    });
    devicesApi.getMyDevices.mockResolvedValue({
      data: [{ id: 7, public_key: "my-key" }],
    });
    encryptMessage.mockResolvedValue({
      ciphertext: "encrypted-text",
      deviceKeys: [{ device_id: 5, encrypted_key: "wrapped" }],
    });
    messagesApi.send.mockResolvedValue({});
    const onClose = vi.fn();

    renderModal({ onClose });

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "recipient" },
    });
    fireEvent.change(screen.getByPlaceholderText("Write your message..."), {
      target: { value: "Secret!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(messagesApi.send).toHaveBeenCalledWith({
        recipient_id: 99,
        ciphertext: "encrypted-text",
        device_keys: [{ device_id: 5, encrypted_key: "wrapped" }],
      });
    });
  });

  it("shows error on user not found", async () => {
    usersApi.getUser.mockRejectedValue({ response: { status: 404 } });

    renderModal();

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "nobody" },
    });
    fireEvent.change(screen.getByPlaceholderText("Write your message..."), {
      target: { value: "Hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("User not found");
    });
  });

  it("shows encryption note", () => {
    renderModal();
    expect(screen.getByText(/end-to-end encrypted/i)).toBeInTheDocument();
  });
});
