import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockAddToast = vi.fn();
const mockUpload = vi.fn();
const mockCreate = vi.fn();

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../api/stories", () => ({
  create: (...args) => mockCreate(...args),
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
  default: ({ children, loading, ...props }) => (
    <button {...props} disabled={props.disabled || loading}>
      {loading ? "Loading..." : children}
    </button>
  ),
}));

vi.mock("./ui/icons/ImageIcon", () => ({
  default: () => <span data-testid="image-icon" />,
}));

import StoryCompose from "./StoryCompose";

describe("StoryCompose", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock URL.createObjectURL
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

  it("renders image picker when open and no file selected", () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "New story");
    expect(screen.getByLabelText("Choose image")).toBeInTheDocument();
  });

  it("shows preview and form after selecting an image", async () => {
    render(<StoryCompose open={true} onClose={vi.fn()} />);

    // Simulate file selection
    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByAltText("Preview")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("Add a caption...")).toBeInTheDocument();
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

  it("submits story successfully", async () => {
    const onClose = vi.fn();
    mockUpload.mockResolvedValue({ data: { url: "/uploaded.webp" } });
    mockCreate.mockResolvedValue({});

    render(<StoryCompose open={true} onClose={onClose} />);

    // Select file
    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(["img"], "photo.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Add a caption...")).toBeInTheDocument();
    });

    // Add caption
    fireEvent.change(screen.getByPlaceholderText("Add a caption..."), {
      target: { value: "My caption" },
    });

    // Submit
    fireEvent.click(screen.getByText("Post story"));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith(file, "post_image");
      expect(mockCreate).toHaveBeenCalledWith({
        image_url: "/uploaded.webp",
        caption: "My caption",
        duration_hours: 24,
      });
      expect(mockAddToast).toHaveBeenCalledWith("Story posted!", "success");
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("shows error toast on submission failure", async () => {
    mockUpload.mockRejectedValue(new Error("fail"));

    render(<StoryCompose open={true} onClose={vi.fn()} />);

    // Select file
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
});
