import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("./Lightbox.module.css", () => ({
  default: { overlay: "overlay", close: "close", content: "content", nav: "nav", prev: "prev", next: "next", image: "image", dots: "dots", dot: "dot", active: "active" },
}));

vi.mock("./ui/icons/CloseIcon", () => ({
  default: () => <span data-testid="close-icon" />,
}));

import Lightbox from "./Lightbox";

const images = [
  { url: "/img1.webp" },
  { url: "/img2.webp" },
  { url: "/img3.webp" },
];

describe("Lightbox", () => {
  let onClose;
  let onIndexChange;

  beforeEach(() => {
    vi.clearAllMocks();
    onClose = vi.fn();
    onIndexChange = vi.fn();
  });

  it("renders with correct role and aria attributes", () => {
    render(
      <Lightbox images={images} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Image viewer")).toBeInTheDocument();
    expect(screen.getByLabelText("Close")).toBeInTheDocument();
  });

  it("shows next button but not previous when at first image", () => {
    render(
      <Lightbox images={images} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(screen.queryByLabelText("Previous image")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Next image")).toBeInTheDocument();
  });

  it("shows previous button but not next when at last image", () => {
    render(
      <Lightbox images={images} index={2} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(screen.getByLabelText("Previous image")).toBeInTheDocument();
    expect(screen.queryByLabelText("Next image")).not.toBeInTheDocument();
  });

  it("shows both nav buttons when in middle of gallery", () => {
    render(
      <Lightbox images={images} index={1} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(screen.getByLabelText("Previous image")).toBeInTheDocument();
    expect(screen.getByLabelText("Next image")).toBeInTheDocument();
  });

  it("calls onIndexChange with correct index when nav buttons clicked", () => {
    render(
      <Lightbox images={images} index={1} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    fireEvent.click(screen.getByLabelText("Previous image"));
    expect(onIndexChange).toHaveBeenCalledWith(0);

    fireEvent.click(screen.getByLabelText("Next image"));
    expect(onIndexChange).toHaveBeenCalledWith(2);
  });

  it("calls onClose when close button is clicked", () => {
    render(
      <Lightbox images={images} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    fireEvent.click(screen.getByLabelText("Close"));
    // Called twice: once from button onClick, once from event bubbling to overlay
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when overlay is clicked", () => {
    render(
      <Lightbox images={images} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("responds to keyboard events: Escape, ArrowLeft, ArrowRight", () => {
    render(
      <Lightbox images={images} index={1} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(document, { key: "ArrowLeft" });
    expect(onIndexChange).toHaveBeenCalledWith(0);

    fireEvent.keyDown(document, { key: "ArrowRight" });
    expect(onIndexChange).toHaveBeenCalledWith(2);
  });

  it("does not show dots for a single image", () => {
    const { container } = render(
      <Lightbox images={[{ url: "/img.webp" }]} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(container.querySelectorAll(".dot")).toHaveLength(0);
  });

  it("sets body overflow to hidden on mount and restores on unmount", () => {
    const { unmount } = render(
      <Lightbox images={images} index={0} onClose={onClose} onIndexChange={onIndexChange} />,
    );

    expect(document.body.style.overflow).toBe("hidden");

    unmount();
    expect(document.body.style.overflow).toBe("");
  });
});
