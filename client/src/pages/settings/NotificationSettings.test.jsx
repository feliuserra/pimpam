import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import NotificationSettings from "./NotificationSettings";

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
  })),
}));

vi.mock("../../api/notifications", () => ({
  getPreferences: vi.fn(),
  updatePreference: vi.fn(),
}));

import * as notificationsApi from "../../api/notifications";

describe("NotificationSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads preferences from API", async () => {
    notificationsApi.getPreferences.mockResolvedValue({ data: ["vote"] });

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(notificationsApi.getPreferences).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    });
  });

  it("renders 14 toggle switches", async () => {
    notificationsApi.getPreferences.mockResolvedValue({ data: [] });

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText("Notification Preferences")).toBeInTheDocument();
    });

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(14);
  });

  it("toggling calls updatePreference API", async () => {
    notificationsApi.getPreferences.mockResolvedValue({ data: [] });
    notificationsApi.updatePreference.mockResolvedValue({});

    render(<NotificationSettings />);

    await waitFor(() => {
      expect(screen.getByText("New followers")).toBeInTheDocument();
    });

    // All enabled by default (none disabled), so the "New followers" checkbox is checked
    const followCheckbox = screen.getByRole("checkbox", { name: /new followers/i });
    expect(followCheckbox).toBeChecked();

    fireEvent.click(followCheckbox);

    await waitFor(() => {
      expect(notificationsApi.updatePreference).toHaveBeenCalledWith("follow", false);
    });
  });
});
