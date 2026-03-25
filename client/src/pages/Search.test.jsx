import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/search", () => ({
  search: vi.fn(),
}));

// Mock routing
const mockSetParams = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: vi.fn(() => [new URLSearchParams("q=test"), mockSetParams]),
    useNavigate: vi.fn(() => vi.fn()),
    Link: ({ children, to }) => <a href={to}>{children}</a>,
  };
});

// Mock contexts
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));
vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));
vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
    clearNotifications: vi.fn(),
    decrementNotifications: vi.fn(),
  })),
}));
vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => vi.fn()),
}));

// Mock complex child components
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));
vi.mock("../components/PostCard", () => ({
  default: ({ post }) => <div data-testid="post-card">{post.title}</div>,
}));
vi.mock("../components/UserCard", () => ({
  default: ({ user }) => <div data-testid="user-card">{user.username}</div>,
}));
vi.mock("../components/CommunityCard", () => ({
  default: ({ community }) => (
    <div data-testid="community-card">{community.name}</div>
  ),
}));

import * as searchApi from "../api/search";
import { useSearchParams } from "react-router-dom";
import Search from "./Search";

beforeEach(() => {
  vi.clearAllMocks();
  useSearchParams.mockReturnValue([
    new URLSearchParams("q=test"),
    mockSetParams,
  ]);
});

describe("Search", () => {
  it("shows search input", () => {
    searchApi.search.mockReturnValue(new Promise(() => {}));

    render(<Search />);

    expect(
      screen.getByPlaceholderText("Search posts, users, communities..."),
    ).toBeInTheDocument();
  });

  it("submitting search updates URL params", () => {
    searchApi.search.mockReturnValue(new Promise(() => {}));

    render(<Search />);

    const input = screen.getByPlaceholderText(
      "Search posts, users, communities...",
    );
    fireEvent.change(input, { target: { value: "new query" } });
    fireEvent.submit(input.closest("form"));

    expect(mockSetParams).toHaveBeenCalledWith({ q: "new query" });
  });

  it("renders results from API", async () => {
    const results = {
      hits: [
        { id: 1, title: "Result Post", content: "body" },
        { id: 2, username: "founduser", display_name: "Found" },
        { id: 3, name: "techcommunity", member_count: 100 },
      ],
      total: 3,
    };
    searchApi.search.mockResolvedValue({ data: results });

    render(<Search />);

    await waitFor(() => {
      expect(screen.getByText("3 results")).toBeInTheDocument();
    });

    expect(screen.getByTestId("post-card")).toBeInTheDocument();
    expect(screen.getByTestId("user-card")).toBeInTheDocument();
    expect(screen.getByTestId("community-card")).toBeInTheDocument();
  });

  it("shows 'No results' when empty", async () => {
    searchApi.search.mockResolvedValue({ data: { hits: [], total: 0 } });

    render(<Search />);

    await waitFor(() => {
      expect(screen.getByText(/no results/i)).toBeInTheDocument();
    });
  });

  it("tabs filter by type", async () => {
    searchApi.search.mockResolvedValue({
      data: { hits: [{ id: 1, username: "someone" }], total: 1 },
    });

    render(<Search />);

    // Wait for initial results to load
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();
    });

    // Click the "Users" tab
    fireEvent.click(screen.getByRole("tab", { name: "Users" }));

    await waitFor(() => {
      expect(searchApi.search).toHaveBeenCalledWith(
        expect.objectContaining({ type: "user" }),
      );
    });
  });

  it("shows hint text when no query provided", () => {
    useSearchParams.mockReturnValue([new URLSearchParams(""), mockSetParams]);

    render(<Search />);

    expect(
      screen.getByText("Search for posts, users, or communities."),
    ).toBeInTheDocument();
  });
});
