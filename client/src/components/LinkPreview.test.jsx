import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("./LinkPreview.module.css", () => ({
  default: { card: "card", image: "image", body: "body", site: "site", title: "title", description: "description" },
}));

vi.mock("./ui/Skeleton", () => ({
  default: () => <span data-testid="skeleton" />,
}));

vi.mock("../api/posts", () => ({
  getLinkPreview: vi.fn(),
}));

import LinkPreview from "./LinkPreview";
import * as postsApi from "../api/posts";

describe("LinkPreview", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when url is not provided", () => {
    const { container } = render(<LinkPreview />);
    expect(container.innerHTML).toBe("");
  });

  it("shows skeleton while loading", () => {
    postsApi.getLinkPreview.mockReturnValue(new Promise(() => {})); // never resolves

    render(<LinkPreview url="https://example.com" />);

    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });

  it("renders preview card with title and description", async () => {
    postsApi.getLinkPreview.mockResolvedValue({
      data: {
        title: "Example Title",
        description: "Example description text",
        site_name: "Example.com",
        image: null,
      },
    });

    render(<LinkPreview url="https://example.com" />);

    await waitFor(() => {
      expect(screen.getByText("Example Title")).toBeInTheDocument();
    });

    expect(screen.getByText("Example description text")).toBeInTheDocument();
    expect(screen.getByText("Example.com")).toBeInTheDocument();
  });

  it("renders preview image when available", async () => {
    postsApi.getLinkPreview.mockResolvedValue({
      data: {
        title: "With Image",
        image: "https://example.com/og.jpg",
      },
    });

    render(<LinkPreview url="https://example.com" />);

    await waitFor(() => {
      expect(screen.getByText("With Image")).toBeInTheDocument();
    });

    // alt="" makes image presentational, so query by tag
    const img = document.querySelector("img");
    expect(img).toHaveAttribute("src", "https://example.com/og.jpg");
  });

  it("returns null after loading when no title or image", async () => {
    postsApi.getLinkPreview.mockResolvedValue({
      data: { title: null, image: null },
    });

    const { container } = render(<LinkPreview url="https://example.com" />);

    await waitFor(() => {
      expect(screen.queryAllByTestId("skeleton")).toHaveLength(0);
    });

    expect(container.innerHTML).toBe("");
  });

  it("opens link in new tab with security attributes", async () => {
    postsApi.getLinkPreview.mockResolvedValue({
      data: { title: "Link", image: null },
    });

    render(<LinkPreview url="https://example.com/page" />);

    await waitFor(() => {
      expect(screen.getByText("Link")).toBeInTheDocument();
    });

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("href", "https://example.com/page");
  });
});
