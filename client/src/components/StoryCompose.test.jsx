import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockAddToast = vi.fn();
const mockUpload = vi.fn();
const mockCreate = vi.fn();
const mockAutocompleteUsers = vi.fn();
const mockGetLinkPreview = vi.fn();

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../api/stories", () => ({
  create: (...args) => mockCreate(...args),
}));

vi.mock("../api/media", () => ({
  upload: (...args) => mockUpload(...args),
}));

vi.mock("../api/users", () => ({
  autocompleteUsers: (...args) => mockAutocompleteUsers(...args),
}));

vi.mock("../api/posts", () => ({
  getLinkPreview: (...args) => mockGetLinkPreview(...args),
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
  default: ({ children, loading, ...props }) => (
    <button {...props} disabled={props.disabled || loading}>
      {loading ? "Loading..." : children}
    </button>
  ),
}));

vi.mock("./ui/icons/ImageIcon", () => ({
  default: () => <span data-testid="image-icon" />,
}));

vi.mock("./ui/Avatar", () => ({
  default: ({ username }) => <span data-testid={`avatar-${username}`} />,
}));

vi.mock("../api/friendGroups", () => ({
  getCloseFriends: vi.fn(() => Promise.resolve({ data: { member_count: 3 } })),
}));

vi.mock("./ui/InfoTooltip", () => ({
  default: ({ children }) => <span data-testid="info-tooltip">{children}</span>,
}));

import StoryCompose from "./StoryCompose";

const CAPTION_PLACEHOLDER = "Add a caption... use @ to tag people";

describe("StoryCompose", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:http://localhost/fake"),
      revokeObjectURL: vi.fn(),
    });
  });

  it("does not render when open is false", () => {
    render(<StoryCompose open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders story type toggle and image picker when open", () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "New story");
    expect(screen.getByText("Image")).toBeInTheDocument();
    expect(screen.getByText("Link")).toBeInTheDocument();
    expect(screen.getByText("Image + Link")).toBeInTheDocument();
    expect(screen.getByLabelText("Choose image")).toBeInTheDocument();
  });

  it("shows preview and form after selecting an image", async () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByAltText("Preview")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(CAPTION_PLACEHOLDER)).toBeInTheDocument();
      expect(screen.getByText("Post story")).toBeInTheDocument();
    });
  });

  it("shows duration options after selecting an image", async () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("12h")).toBeInTheDocument();
      expect(screen.getByText("24h")).toBeInTheDocument();
      expect(screen.getByText("48h")).toBeInTheDocument();
      expect(screen.getByText("7 days")).toBeInTheDocument();
    });
  });

  it("submits image story successfully", async () => {
    const onClose = vi.fn();
    mockUpload.mockResolvedValue({ data: { url: "/uploaded-signed.webp", key: "users/1/post-images/abc" } });
    mockCreate.mockResolvedValue({});

    render(<StoryCompose open={true} onClose={onClose} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(CAPTION_PLACEHOLDER)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(CAPTION_PLACEHOLDER), {
      target: { value: "My caption" },
    });

    fireEvent.click(screen.getByText("Post story"));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, "post_image");
      expect(mockCreate).toHaveBeenCalledWith({
        image_url: "users/1/post-images/abc",
        caption: "My caption",
        duration_hours: 24,
        visibility: "close_friends",
      });
      expect(mockAddToast).toHaveBeenCalledWith("Story posted!", "success");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("shows error toast on submission failure", async () => {
    mockUpload.mockRejectedValue(new Error("fail"));

    render(<StoryCompose open={true} onClose={vi.fn()} />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Post story")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Post story"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith("Failed to post story.", "error");
    });
  });

  it("shows link URL input when Link type is selected", async () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    fireEvent.click(screen.getByText("Link"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("https://...")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(CAPTION_PLACEHOLDER)).toBeInTheDocument();
    });
  });

  it("submits link-only story", async () => {
    const onClose = vi.fn();
    mockCreate.mockResolvedValue({});
    mockGetLinkPreview.mockResolvedValue({ data: {} });

    render(<StoryCompose open={true} onClose={onClose} />);

    fireEvent.click(screen.getByText("Link"));

    await waitFor(() => {
      expect(screen.getByPlaceholderText("https://...")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("https://..."), {
      target: { value: "https://example.com" },
    });

    fireEvent.click(screen.getByText("Post story"));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        link_url: "https://example.com",
        caption: null,
        duration_hours: 24,
        visibility: "close_friends",
      });
    });
  });
});
