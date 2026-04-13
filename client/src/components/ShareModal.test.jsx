import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

const mockAddToast = vi.fn();
const mockShare = vi.fn();
const mockListJoined = vi.fn();
const mockNavigate = vi.fn();
const mockAutocomplete = vi.fn();
const mockGetUser = vi.fn();
const mockSendMessage = vi.fn();
const mockEncrypt = vi.fn();
const mockGetUserDeviceKeys = vi.fn();
const mockGetMyDevices = vi.fn();

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, username: "testuser" },
  })),
}));

vi.mock("../api/posts", () => ({
  share: (...args) => mockShare(...args),
}));

vi.mock("../api/communities", () => ({
  listJoined: (...args) => mockListJoined(...args),
}));

vi.mock("../api/users", () => ({
  autocompleteUsers: (...args) => mockAutocomplete(...args),
  getUser: (...args) => mockGetUser(...args),
}));

vi.mock("../api/messages", () => ({
  send: (...args) => mockSendMessage(...args),
}));

vi.mock("../api/devices", () => ({
  getUserDeviceKeys: (...args) => mockGetUserDeviceKeys(...args),
  getMyDevices: (...args) => mockGetMyDevices(...args),
}));

vi.mock("../crypto/encrypt", () => ({
  encryptMessage: (...args) => mockEncrypt(...args),
}));

vi.mock("./ui/Modal", () => ({
  default: ({ open, onClose, title, children }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        <button onClick={onClose} aria-label="Close">
          X
        </button>
        {children}
      </div>
    ) : null,
}));

vi.mock("./ui/Spinner", () => ({
  default: () => <span data-testid="spinner">Loading...</span>,
}));

vi.mock("./ui/Avatar", () => ({
  default: ({ alt }) => <span data-testid="avatar">{alt}</span>,
}));

vi.mock("./ui/InfoTooltip", () => ({
  default: ({ children }) => <span data-testid="infotooltip">{children}</span>,
}));

import ShareModal from "./ShareModal";

const testPost = {
  id: 10,
  title: "Test Post",
  image_url: "http://img.test/1.jpg",
  author_username: "author1",
  author_avatar_url: null,
  community_name: "tech",
};

describe("ShareModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListJoined.mockResolvedValue({ data: [] });
  });

  it("does not render when open is false", () => {
    render(
      <ShareModal
        open={false}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders with Send to and Reshare tabs", async () => {
    render(
      <ShareModal
        open={true}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );

    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "Share post",
    );
    // "Send to" appears both as tab and as label text — check both exist
    expect(screen.getAllByText("Send to").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Reshare")).toBeInTheDocument();
  });

  it("defaults to Send to tab with post preview", () => {
    render(
      <ShareModal
        open={true}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );

    // Post preview card
    expect(screen.getByText("Test Post")).toBeInTheDocument();
    expect(screen.getByText(/@author1/)).toBeInTheDocument();
    // User search input
    expect(
      screen.getByPlaceholderText("Search for a user..."),
    ).toBeInTheDocument();
    // Encryption badge
    expect(screen.getByText("End-to-end encrypted")).toBeInTheDocument();
  });

  it("shows encryption InfoTooltip with AES-256-GCM details", () => {
    render(
      <ShareModal
        open={true}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );

    expect(screen.getByTestId("infotooltip")).toBeInTheDocument();
    expect(screen.getByText(/AES-256-GCM/)).toBeInTheDocument();
    expect(screen.getByText(/RSA-OAEP/)).toBeInTheDocument();
  });

  it("switches to Reshare tab with share form", () => {
    render(
      <ShareModal
        open={true}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );

    fireEvent.click(screen.getByText("Reshare"));
    expect(
      screen.getByPlaceholderText("Add a comment (optional)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Your profile")).toBeInTheDocument();
  });

  it("submits reshare without comment", async () => {
    const onClose = vi.fn();
    mockShare.mockResolvedValue({});

    render(
      <ShareModal
        open={true}
        onClose={onClose}
        postId={10}
        post={testPost}
      />,
    );

    fireEvent.click(screen.getByText("Reshare"));
    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockShare).toHaveBeenCalledWith(10, {});
      expect(mockAddToast).toHaveBeenCalledWith("Post shared!", "success");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("shows already shared error", async () => {
    mockShare.mockRejectedValue({
      response: { data: { detail: "already_shared" } },
    });

    render(
      <ShareModal
        open={true}
        onClose={vi.fn()}
        postId={10}
        post={testPost}
      />,
    );

    fireEvent.click(screen.getByText("Reshare"));
    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith(
        "You already shared this post",
        "error",
      );
    });
  });

  it("sends a post as DM to selected user", async () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    mockAutocomplete.mockResolvedValue({
      data: [{ id: 2, username: "bob", avatar_url: null }],
    });
    mockGetUser.mockResolvedValue({
      data: { id: 2 },
    });
    mockGetUserDeviceKeys.mockResolvedValue({
      data: [{ device_id: 10, public_key: "bobpubkey", public_key_fingerprint: "abc" }],
    });
    mockGetMyDevices.mockResolvedValue({
      data: [{ id: 5, public_key: "mypubkey", device_name: "Chrome" }],
    });
    mockEncrypt.mockResolvedValue({
      ciphertext: "enc_text",
      deviceKeys: [
        { device_id: 10, encrypted_key: "bob_wrapped" },
        { device_id: 5, encrypted_key: "my_wrapped" },
      ],
    });
    mockSendMessage.mockResolvedValue({});

    render(
      <ShareModal
        open={true}
        onClose={onClose}
        postId={10}
        post={testPost}
      />,
    );

    // Search for a user
    const input = screen.getByPlaceholderText("Search for a user...");
    await act(async () => {
      fireEvent.change(input, { target: { value: "bob" } });
    });

    // Advance past the 300ms debounce and flush promises
    await act(async () => {
      vi.advanceTimersByTime(400);
    });

    // Autocomplete results should now be rendered
    expect(mockAutocomplete).toHaveBeenCalledWith("bob", 8);
    // Avatar mock and span both render "@bob", so use getAllByText
    const bobElements = screen.getAllByText("@bob");
    expect(bobElements.length).toBeGreaterThanOrEqual(1);

    // Select user — click the button containing "@bob"
    const userButton = bobElements[0].closest("button") || bobElements[1]?.closest("button");
    await act(async () => {
      fireEvent.click(userButton);
    });

    // Submit
    await act(async () => {
      fireEvent.click(screen.getByText("Send"));
    });

    // Flush async operations
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    expect(mockGetUserDeviceKeys).toHaveBeenCalledWith("bob");
    expect(mockEncrypt).toHaveBeenCalled();
    expect(mockSendMessage).toHaveBeenCalledWith({
      recipient_id: 2,
      ciphertext: "enc_text",
      device_keys: [
        { device_id: 10, encrypted_key: "bob_wrapped" },
        { device_id: 5, encrypted_key: "my_wrapped" },
      ],
      shared_post_id: 10,
    });
    expect(mockAddToast).toHaveBeenCalledWith("Sent to @bob", "success");
    expect(onClose).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/messages/2");

    vi.useRealTimers();
  });
});
