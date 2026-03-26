import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import DataSettings from "./DataSettings";

const mockUseAuth = vi.fn(() => ({
  user: { id: 1, username: "testuser", totp_enabled: false, deletion_scheduled_at: null },
  updateUser: vi.fn(),
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: (...args) => mockUseAuth(...args),
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

vi.mock("../../api/users", () => ({
  exportData: vi.fn(),
  deleteAccount: vi.fn(),
  cancelDeletion: vi.fn(),
}));

import * as usersApi from "../../api/users";

describe("DataSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { id: 1, username: "testuser", totp_enabled: false, deletion_scheduled_at: null },
      updateUser: vi.fn(),
    });
  });

  it("renders data export button", () => {
    render(<DataSettings />);
    expect(screen.getByText("Data Export")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /download my data/i })).toBeInTheDocument();
  });

  it("renders delete account form", () => {
    render(<DataSettings />);
    expect(screen.getByText("Delete Account")).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm your password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete my account/i })).toBeInTheDocument();
  });

  it("shows cancel deletion button when scheduled", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 1,
        username: "testuser",
        totp_enabled: false,
        deletion_scheduled_at: "2026-04-01T00:00:00Z",
      },
      updateUser: vi.fn(),
    });

    render(<DataSettings />);

    expect(screen.getByRole("button", { name: /cancel deletion/i })).toBeInTheDocument();
    // The password form should not be visible when deletion is scheduled
    expect(screen.queryByLabelText(/confirm your password/i)).not.toBeInTheDocument();
  });

  it("export button calls exportData API", async () => {
    usersApi.exportData.mockResolvedValue({ data: { posts: [], comments: [] } });

    // Mock URL.createObjectURL and URL.revokeObjectURL
    const mockUrl = "blob:http://localhost/fake";
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => mockUrl),
      revokeObjectURL: vi.fn(),
    });

    render(<DataSettings />);

    fireEvent.click(screen.getByRole("button", { name: /download my data/i }));

    await waitFor(() => {
      expect(usersApi.exportData).toHaveBeenCalled();
    });
  });
});
