import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: vi.fn(() => mockNavigate) };
});

vi.mock("./ui/icons/CloseIcon", () => ({
  default: () => <span data-testid="close-icon">X</span>,
}));

import StoryViewer from "./StoryViewer";

const makeGroup = (items) => ({
  author: { username: "alice", display_name: "Alice", avatar_url: null },
  items,
});

describe("StoryViewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the story image, author name, and close button", () => {
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: "Hello world" },
    ]);

    render(<StoryViewer group={group} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "Story viewer");
    expect(screen.getByAltText("Hello world")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByLabelText("Close")).toBeInTheDocument();
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("uses 'Story' as alt text when no caption", () => {
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: null },
    ]);

    render(<StoryViewer group={group} onClose={vi.fn()} />);

    expect(screen.getByAltText("Story")).toBeInTheDocument();
  });

  it("calls onClose when Close button is clicked", () => {
    const onClose = vi.fn();
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: null },
    ]);

    render(<StoryViewer group={group} onClose={onClose} />);

    fireEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when Escape key is pressed", () => {
    const onClose = vi.fn();
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: null },
    ]);

    render(<StoryViewer group={group} onClose={onClose} />);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("navigates to next story on ArrowRight and calls onClose at end", async () => {
    const onClose = vi.fn();
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: "First" },
      { id: 2, image_url: "/story2.webp", caption: "Second" },
    ]);

    render(<StoryViewer group={group} onClose={onClose} />);

    // Initially shows first story
    expect(screen.getByAltText("First")).toBeInTheDocument();

    // Arrow right goes to next
    fireEvent.keyDown(document, { key: "ArrowRight" });
    await waitFor(() => {
      expect(screen.getByAltText("Second")).toBeInTheDocument();
    });

    // Arrow right at last story calls onClose
    fireEvent.keyDown(document, { key: "ArrowRight" });
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("navigates to author profile when author button is clicked", () => {
    const onClose = vi.fn();
    const group = makeGroup([
      { id: 1, image_url: "/story1.webp", caption: null },
    ]);

    render(<StoryViewer group={group} onClose={onClose} />);

    fireEvent.click(screen.getByText("Alice"));
    expect(onClose).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/u/alice");
  });
});
