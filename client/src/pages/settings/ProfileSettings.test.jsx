import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../../api/users", () => ({
  updateMe: vi.fn(),
}));
vi.mock("../../api/media", () => ({
  upload: vi.fn(),
}));

// Mock contexts
const mockUpdateUser = vi.fn();
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: {
      id: 1,
      username: "testuser",
      display_name: "Test User",
      bio: "My bio",
      avatar_url: "https://example.com/avatar.jpg",
    },
    updateUser: mockUpdateUser,
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

// Mock child components
vi.mock("../../components/ui/Avatar", () => ({
  default: ({ alt }) => <img data-testid="avatar" alt={alt} />,
}));

import * as usersApi from "../../api/users";
import * as mediaApi from "../../api/media";
import ProfileSettings from "./ProfileSettings";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProfileSettings", () => {
  it("renders profile form with current user data", () => {
    render(<ProfileSettings />);

    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();
    expect(screen.getByDisplayValue("My bio")).toBeInTheDocument();
    expect(screen.getByTestId("avatar")).toBeInTheDocument();
    expect(screen.getByText("Change photo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });

  it("renders display name and bio labels", () => {
    render(<ProfileSettings />);

    expect(screen.getByText("Display name")).toBeInTheDocument();
    expect(screen.getByText("Bio")).toBeInTheDocument();
  });

  it("submits profile update and shows success message", async () => {
    const updatedUser = {
      id: 1,
      username: "testuser",
      display_name: "New Name",
      bio: "Updated bio",
      avatar_url: "https://example.com/avatar.jpg",
    };
    usersApi.updateMe.mockResolvedValue({ data: updatedUser });

    render(<ProfileSettings />);

    // Change display name
    fireEvent.change(screen.getByDisplayValue("Test User"), {
      target: { value: "New Name" },
    });

    // Change bio
    fireEvent.change(screen.getByDisplayValue("My bio"), {
      target: { value: "Updated bio" },
    });

    // Submit form
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(usersApi.updateMe).toHaveBeenCalledWith({
        display_name: "New Name",
        bio: "Updated bio",
        avatar_url: "https://example.com/avatar.jpg",
      });
    });

    await waitFor(() => {
      expect(screen.getByText("Profile updated.")).toBeInTheDocument();
    });

    expect(mockUpdateUser).toHaveBeenCalledWith(updatedUser);
  });

  it("shows error message when save fails", async () => {
    usersApi.updateMe.mockRejectedValue(new Error("Server error"));

    render(<ProfileSettings />);

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("Failed to save profile")).toBeInTheDocument();
    });
  });

  it("shows 'Saving...' text while submitting", async () => {
    usersApi.updateMe.mockReturnValue(new Promise(() => {}));

    render(<ProfileSettings />);

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });
  });

  it("uploads avatar and updates preview", async () => {
    mediaApi.upload.mockResolvedValue({
      data: { url: "https://example.com/new-avatar.jpg" },
    });

    render(<ProfileSettings />);

    const fileInput = screen.getByLabelText("Change photo").querySelector("input[type='file']")
      || document.querySelector("input[type='file']");

    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(mediaApi.upload).toHaveBeenCalledWith(file, "avatar");
    });
  });

  it("shows error when avatar upload fails", async () => {
    mediaApi.upload.mockRejectedValue(new Error("Upload error"));

    render(<ProfileSettings />);

    const fileInput = document.querySelector("input[type='file']");
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Failed to upload image")).toBeInTheDocument();
    });
  });
});
