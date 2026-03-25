import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("./Header.module.css", () => ({ default: {} }));

import Header from "./Header";

describe("Header", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders left and right content", () => {
    render(
      <Header
        left={<span>Left Content</span>}
        right={<span>Right Content</span>}
      />,
    );

    expect(screen.getByText("Left Content")).toBeInTheDocument();
    expect(screen.getByText("Right Content")).toBeInTheDocument();
  });

  it("renders a header element", () => {
    render(<Header left="Title" right={null} />);

    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("renders without right content", () => {
    render(<Header left={<h1>Page Title</h1>} />);

    expect(screen.getByText("Page Title")).toBeInTheDocument();
  });

  it("renders without left content", () => {
    render(<Header right={<button>Action</button>} />);

    expect(screen.getByText("Action")).toBeInTheDocument();
  });
});
