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

import * as usersApi from "../api/users";
import * as messagesApi from "../api/messages";
import * as devicesApi from "../api/devices";

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

  it("submitting looks up user then sends message", async () => {
    usersApi.getUser.mockResolvedValue({ data: { id: 99, username: "recipient" } });
    devicesApi.getUserDeviceKeys.mockResolvedValue({ data: [] });
    devicesApi.getMyDevices.mockResolvedValue({ data: [] });
    messagesApi.send.mockResolvedValue({});
    const onClose = vi.fn();

    renderModal({ onClose });

    fireEvent.change(screen.getByPlaceholderText("@username"), {
      target: { value: "recipient" },
    });
    fireEvent.change(screen.getByPlaceholderText("Write your message..."), {
      target: { value: "Hi there!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(usersApi.getUser).toHaveBeenCalledWith("recipient");
    });

    await waitFor(() => {
      expect(messagesApi.send).toHaveBeenCalledWith({
        recipient_id: 99,
        ciphertext: "Hi there!",
        device_keys: [],
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
});
