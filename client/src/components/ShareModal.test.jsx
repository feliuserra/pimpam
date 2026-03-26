import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockAddToast = vi.fn();
const mockShare = vi.fn();
const mockListJoined = vi.fn();

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../api/posts", () => ({
  share: (...args) => mockShare(...args),
}));

vi.mock("../api/communities", () => ({
  listJoined: (...args) => mockListJoined(...args),
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

vi.mock("./ui/Spinner", () => ({
  default: () => <span data-testid="spinner">Loading...</span>,
}));

import ShareModal from "./ShareModal";

describe("ShareModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListJoined.mockResolvedValue({ data: [] });
  });

  it("does not render when open is false", () => {
    render(<ShareModal open={false} onClose={vi.fn()} postId={10} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders form with comment textarea and share button when open", async () => {
    render(<ShareModal open={true} onClose={vi.fn()} postId={10} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "Share post");
    expect(screen.getByPlaceholderText("Add a comment (optional)")).toBeInTheDocument();
    expect(screen.getByText("Share")).toBeInTheDocument();
    expect(screen.getByText("Your profile")).toBeInTheDocument();
  });

  it("renders community selector when user has communities", async () => {
    mockListJoined.mockResolvedValue({
      data: [
        { id: 5, name: "tech" },
        { id: 6, name: "music" },
      ],
    });

    render(<ShareModal open={true} onClose={vi.fn()} postId={10} />);

    await waitFor(() => {
      expect(screen.getByText("Your profile")).toBeInTheDocument();
    });
  });

  it("submits share without comment or community", async () => {
    const onClose = vi.fn();
    mockShare.mockResolvedValue({});

    render(<ShareModal open={true} onClose={onClose} postId={10} />);

    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockShare).toHaveBeenCalledWith(10, {});
      expect(mockAddToast).toHaveBeenCalledWith("Post shared!", "success");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("submits share with comment", async () => {
    const onClose = vi.fn();
    mockShare.mockResolvedValue({});

    render(<ShareModal open={true} onClose={onClose} postId={10} />);

    fireEvent.change(screen.getByPlaceholderText("Add a comment (optional)"), {
      target: { value: "Check this out!" },
    });

    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockShare).toHaveBeenCalledWith(10, { comment: "Check this out!" });
      expect(mockAddToast).toHaveBeenCalledWith("Post shared!", "success");
    });
  });

  it("shows already shared error", async () => {
    mockShare.mockRejectedValue({
      response: { data: { detail: "already_shared" } },
    });

    render(<ShareModal open={true} onClose={vi.fn()} postId={10} />);

    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("You already shared this post", "error");
    });
  });

  it("shows generic error on failure", async () => {
    mockShare.mockRejectedValue(new Error("network"));

    render(<ShareModal open={true} onClose={vi.fn()} postId={10} />);

    fireEvent.click(screen.getByText("Share"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("Failed to share", "error");
    });
  });
});
