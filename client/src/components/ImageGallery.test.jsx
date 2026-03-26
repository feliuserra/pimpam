import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

vi.mock("./ImageGallery.module.css", () => ({
  default: { gallery: "gallery", single: "single", double: "double", grid: "grid", imageBtn: "imageBtn", image: "image", more: "more" },
}));

vi.mock("./Lightbox", () => ({
  default: ({ images, index, onClose }) => (
    <div data-testid="lightbox" data-index={index}>
      <button onClick={onClose}>Close lightbox</button>
    </div>
  ),
}));

import ImageGallery from "./ImageGallery";

describe("ImageGallery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when images is empty or undefined", () => {
    const { container: c1 } = render(<ImageGallery images={[]} />);
    expect(c1.innerHTML).toBe("");

    const { container: c2 } = render(<ImageGallery images={null} />);
    expect(c2.innerHTML).toBe("");

    const { container: c3 } = render(<ImageGallery />);
    expect(c3.innerHTML).toBe("");
  });

  it("renders image buttons with correct aria-labels", () => {
    const images = [
      { url: "/img1.webp" },
      { url: "/img2.webp" },
    ];
    render(<ImageGallery images={images} />);

    expect(screen.getByLabelText("View image 1")).toBeInTheDocument();
    expect(screen.getByLabelText("View image 2")).toBeInTheDocument();
  });

  it("shows +N badge when more than 4 images", () => {
    const images = [
      { url: "/img1.webp" },
      { url: "/img2.webp" },
      { url: "/img3.webp" },
      { url: "/img4.webp" },
      { url: "/img5.webp" },
      { url: "/img6.webp" },
    ];
    render(<ImageGallery images={images} />);

    // Only first 4 images rendered
    expect(screen.getAllByRole("button")).toHaveLength(4);
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("opens lightbox when an image is clicked", () => {
    const images = [{ url: "/img1.webp" }, { url: "/img2.webp" }];
    render(<ImageGallery images={images} />);

    expect(screen.queryByTestId("lightbox")).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("View image 2"));

    expect(screen.getByTestId("lightbox")).toBeInTheDocument();
    expect(screen.getByTestId("lightbox")).toHaveAttribute("data-index", "1");
  });

  it("closes lightbox when close is triggered", () => {
    const images = [{ url: "/img1.webp" }];
    render(<ImageGallery images={images} />);

    fireEvent.click(screen.getByLabelText("View image 1"));
    expect(screen.getByTestId("lightbox")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close lightbox"));
    expect(screen.queryByTestId("lightbox")).not.toBeInTheDocument();
  });
});
