import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("./PostCard.module.css", () => ({
  default: { card: "card", authorRow: "authorRow", actions: "actions" },
}));

vi.mock("./ui/Skeleton", () => ({
  default: ({ width, height, rounded }) => (
    <span
      data-testid="skeleton"
      data-width={width}
      data-height={height}
      data-rounded={rounded ? "true" : undefined}
      aria-hidden="true"
    />
  ),
}));

import PostCardSkeleton from "./PostCardSkeleton";

describe("PostCardSkeleton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders multiple skeleton elements", () => {
    render(<PostCardSkeleton />);

    const skeletons = screen.getAllByTestId("skeleton");
    expect(skeletons.length).toBeGreaterThanOrEqual(7);
  });

  it("is hidden from screen readers with aria-hidden", () => {
    const { container } = render(<PostCardSkeleton />);

    const card = container.firstChild;
    expect(card).toHaveAttribute("aria-hidden", "true");
  });

  it("includes a rounded skeleton for the avatar placeholder", () => {
    render(<PostCardSkeleton />);

    const skeletons = screen.getAllByTestId("skeleton");
    const rounded = skeletons.filter((s) => s.getAttribute("data-rounded") === "true");
    expect(rounded.length).toBe(1);
  });
});
