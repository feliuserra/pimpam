import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import AccountSettings from "./AccountSettings";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser", totp_enabled: false, deletion_scheduled_at: null },
    updateUser: vi.fn(),
  })),
}));

vi.mock("../../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));

vi.mock("../../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
    clearNotifications: vi.fn(),
    decrementNotifications: vi.fn(),
    refetch: vi.fn(),
  })),
}));

vi.mock("../../hooks/useTheme", () => ({
  useTheme: vi.fn(() => ({ theme: "light", toggle: vi.fn() })),
}));

vi.mock("../../api/auth", () => ({
  changePassword: vi.fn(),
  totpSetup: vi.fn(),
  totpVerify: vi.fn(),
  totpDisable: vi.fn(),
}));

import * as authApi from "../../api/auth";

describe("AccountSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders change password form", () => {
    render(<AccountSettings />);
    expect(screen.getByText("Change Password")).toBeInTheDocument();
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /update password/i })).toBeInTheDocument();
  });

  it("submitting change password calls API", async () => {
    authApi.changePassword.mockResolvedValue({});

    render(<AccountSettings />);

    fireEvent.change(screen.getByLabelText(/current password/i), {
      target: { value: "oldpass123" },
    });
    fireEvent.change(screen.getByLabelText(/new password/i), {
      target: { value: "Newpass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() => {
      expect(authApi.changePassword).toHaveBeenCalledWith({
        current_password: "oldpass123",
        new_password: "Newpass123",
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/password updated/i)).toBeInTheDocument();
    });
  });

  it("shows 2FA setup section", () => {
    render(<AccountSettings />);
    expect(screen.getByText("Two-Factor Authentication")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /set up 2fa/i })).toBeInTheDocument();
  });

  it("set up 2FA button calls totpSetup API", async () => {
    authApi.totpSetup.mockResolvedValue({
      data: { uri: "otpauth://totp/PimPam:testuser?secret=ABC", secret: "ABC123" },
    });

    render(<AccountSettings />);

    fireEvent.click(screen.getByRole("button", { name: /set up 2fa/i }));

    await waitFor(() => {
      expect(authApi.totpSetup).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText("ABC123")).toBeInTheDocument();
    });
  });
});
