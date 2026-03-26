import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockAddToast = vi.fn();
const mockCreate = vi.fn();
const mockListJoined = vi.fn();
const mockUpload = vi.fn();

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../api/posts", () => ({
  create: (...args) => mockCreate(...args),
}));

vi.mock("../api/communities", () => ({
  listJoined: (...args) => mockListJoined(...args),
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

vi.mock("./ui/Button", () => ({
  default: ({ children, loading, disabled, ...props }) => (
    <button {...props} disabled={disabled || loading}>
      {loading ? "Loading..." : children}
    </button>
  ),
}));

vi.mock("./ui/icons/ImageIcon", () => ({
  default: () => <span data-testid="image-icon" />,
}));

vi.mock("./ui/icons/CloseIcon", () => ({
  default: () => <span data-testid="close-icon" />,
}));

import ComposePost from "./ComposePost";

describe("ComposePost", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListJoined.mockResolvedValue({ data: [] });
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:http://localhost/fake"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("does not render when open is false", () => {
    render(<ComposePost open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders form fields when open", async () => {
    render(<ComposePost open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "New post");
    expect(screen.getByPlaceholderText("Title *")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Link (optional)")).toBeInTheDocument();
    expect(screen.getByText("Add image")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.getByText("Post")).toBeInTheDocument();
  });

  it("renders community selector when user has joined communities", async () => {
    mockListJoined.mockResolvedValue({
      data: [
        { id: 5, name: "tech" },
        { id: 6, name: "music" },
      ],
    });

    render(<ComposePost open={true} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Community")).toBeInTheDocument();
      expect(screen.getByText("No community (personal)")).toBeInTheDocument();
    });
  });

  it("Post button is disabled when title is empty", () => {
    render(<ComposePost open={true} onClose={vi.fn()} />);

    const postBtn = screen.getByText("Post");
    expect(postBtn).toBeDisabled();
  });

  it("submits post successfully with title and content", async () => {
    const onClose = vi.fn();
    const onCreated = vi.fn();
    mockCreate.mockResolvedValue({ data: { id: 1, title: "My post" } });

    render(
      <ComposePost open={true} onClose={onClose} onCreated={onCreated} />,
    );

    // Fill in title
    fireEvent.change(screen.getByPlaceholderText("Title *"), {
      target: { value: "My post" },
    });

    // Fill in content
    fireEvent.change(screen.getByPlaceholderText("What's on your mind?"), {
      target: { value: "Some content" },
    });

    // Submit the form
    fireEvent.submit(screen.getByPlaceholderText("Title *").closest("form"));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        title: "My post",
        content: "Some content",
        url: null,
        image_url: null,
        community_id: null,
      });
      expect(mockAddToast).toHaveBeenCalledWith("Post created!", "success");
      expect(onClose).toHaveBeenCalled();
      expect(onCreated).toHaveBeenCalledWith({ id: 1, title: "My post" });
    });
  });

  it("shows error toast on submission failure", async () => {
    mockCreate.mockRejectedValue({
      response: { data: { detail: "Rate limited" } },
    });

    render(<ComposePost open={true} onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("Title *"), {
      target: { value: "Test" },
    });

    fireEvent.submit(screen.getByPlaceholderText("Title *").closest("form"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("Rate limited", "error");
    });
  });

  it("calls onClose when Cancel is clicked", () => {
    const onClose = vi.fn();
    render(<ComposePost open={true} onClose={onClose} />);

    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });
});
