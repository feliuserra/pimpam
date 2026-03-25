import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockUpdateUser = vi.fn();
const mockUpdateMe = vi.fn();
const mockUpload = vi.fn();

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: {
      id: 1,
      username: "testuser",
      display_name: "Test User",
      bio: "Hello world",
      avatar_url: "/avatar.webp",
    },
    updateUser: mockUpdateUser,
  })),
}));

vi.mock("../api/users", () => ({
  updateMe: (...args) => mockUpdateMe(...args),
}));

vi.mock("../api/media", () => ({
  upload: (...args) => mockUpload(...args),
}));

vi.mock("./ui/Modal", () => ({
  default: ({ open, onClose, title, children }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        <button onClick={onClose} aria-label="Close">X</button>
        {children}
      </div>
    ) : null,
}));

vi.mock("./ui/Avatar", () => ({
  default: ({ src, alt, size }) => (
    <img data-testid="avatar" src={src} alt={alt} width={size} />
  ),
}));

import EditProfileModal from "./EditProfileModal";

describe("EditProfileModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when open is false", () => {
    render(<EditProfileModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders form with avatar, display name, bio, and save button", () => {
    render(<EditProfileModal open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "Edit Profile");
    expect(screen.getByTestId("avatar")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Your display name")).toHaveValue("Test User");
    expect(screen.getByPlaceholderText("Tell people about yourself")).toHaveValue("Hello world");
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Change photo")).toBeInTheDocument();
  });

  it("updates display name and bio fields", () => {
    render(<EditProfileModal open={true} onClose={vi.fn()} />);

    const nameInput = screen.getByPlaceholderText("Your display name");
    const bioInput = screen.getByPlaceholderText("Tell people about yourself");

    fireEvent.change(nameInput, { target: { value: "New Name" } });
    fireEvent.change(bioInput, { target: { value: "New bio text" } });

    expect(nameInput).toHaveValue("New Name");
    expect(bioInput).toHaveValue("New bio text");
  });

  it("submits profile changes successfully", async () => {
    const onClose = vi.fn();
    mockUpdateMe.mockResolvedValue({
      data: {
        id: 1,
        username: "testuser",
        display_name: "Updated Name",
        bio: "Updated bio",
        avatar_url: "/avatar.webp",
      },
    });

    render(<EditProfileModal open={true} onClose={onClose} />);

    fireEvent.change(screen.getByPlaceholderText("Your display name"), {
      target: { value: "Updated Name" },
    });
    fireEvent.change(screen.getByPlaceholderText("Tell people about yourself"), {
      target: { value: "Updated bio" },
    });

    fireEvent.submit(screen.getByPlaceholderText("Your display name").closest("form"));

    await waitFor(() => {
      expect(mockUpdateMe).toHaveBeenCalledWith({
        display_name: "Updated Name",
        bio: "Updated bio",
        avatar_url: "/avatar.webp",
      });
      expect(mockUpdateUser).toHaveBeenCalledWith(
        expect.objectContaining({ display_name: "Updated Name" }),
      );
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("shows error on save failure", async () => {
    mockUpdateMe.mockRejectedValue(new Error("network"));

    render(<EditProfileModal open={true} onClose={vi.fn()} />);

    fireEvent.submit(screen.getByPlaceholderText("Your display name").closest("form"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to save profile");
    });
  });

  it("uploads new avatar image", async () => {
    mockUpload.mockResolvedValue({
      data: { url: "/new-avatar.webp" },
    });

    render(<EditProfileModal open={true} onClose={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "avatar.png", { type: "image/png" });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, "avatar");
      expect(screen.getByTestId("avatar")).toHaveAttribute("src", "/new-avatar.webp");
    });
  });

  it("shows upload error when avatar upload fails", async () => {
    mockUpload.mockRejectedValue(new Error("upload failed"));

    render(<EditProfileModal open={true} onClose={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "avatar.png", { type: "image/png" });

    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to upload image");
    });
  });
});
