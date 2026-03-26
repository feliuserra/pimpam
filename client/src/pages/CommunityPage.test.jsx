import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/communities", () => ({
  get: vi.fn(),
  listJoined: vi.fn(),
  getPosts: vi.fn(),
  join: vi.fn(),
  leave: vi.fn(),
}));

// Mock routing
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ name: "tech" })),
    useNavigate: vi.fn(() => vi.fn()),
    Link: ({ children, to }) => <a href={to}>{children}</a>,
  };
});

// Mock contexts
const mockUser = { id: 1, username: "testuser" };
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: mockUser })),
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
  useToast: vi.fn(() => ({ addToast: vi.fn() })),
}));

// Mock child components
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
vi.mock("../components/ComposePost", () => ({
  default: ({ open, onClose }) =>
    open ? (
      <div data-testid="compose-post">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));
vi.mock("../components/ui/Spinner", () => ({
  default: () => <div role="status" aria-label="Loading">Loading...</div>,
}));
vi.mock("../components/ui/icons/PlusIcon", () => ({
  default: () => <span>+</span>,
}));

import * as communitiesApi from "../api/communities";
import CommunityPage from "./CommunityPage";

beforeEach(() => {
  global.IntersectionObserver = vi.fn(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  }));
  vi.clearAllMocks();
});

describe("CommunityPage", () => {
  const community = {
    id: 10,
    name: "tech",
    description: "Technology discussions",
    member_count: 1500,
  };

  it("shows spinner while loading community", () => {
    communitiesApi.get.mockReturnValue(new Promise(() => {}));

    render(<CommunityPage />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.getByText("c/tech")).toBeInTheDocument();
  });

  it("renders community info after loading", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });
    communitiesApi.listJoined.mockResolvedValue({ data: [] });
    communitiesApi.getPosts.mockResolvedValue({ data: [] });

    render(<CommunityPage />);

    // Wait for data-dependent text (not "c/tech" which appears in loading state too)
    await waitFor(() => {
      expect(screen.getByText("Technology discussions")).toBeInTheDocument();
    });

    expect(screen.getByText(/1.?500 members/)).toBeInTheDocument();
  });

  it("shows error when community not found", async () => {
    communitiesApi.get.mockRejectedValue(new Error("Not found"));

    render(<CommunityPage />);

    await waitFor(() => {
      expect(screen.getByText("Community not found")).toBeInTheDocument();
    });
  });

  it("shows Join button when user has not joined", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });
    communitiesApi.listJoined.mockResolvedValue({ data: [] });
    communitiesApi.getPosts.mockResolvedValue({ data: [] });

    render(<CommunityPage />);

    await waitFor(() => {
      expect(screen.getByText("Join")).toBeInTheDocument();
    });

    expect(screen.queryByText("Joined")).not.toBeInTheDocument();
  });

  it("shows Joined button and Mod Panel link when user is a member", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });
    communitiesApi.listJoined.mockResolvedValue({
      data: [{ id: 10, name: "tech" }],
    });
    communitiesApi.getPosts.mockResolvedValue({ data: [] });

    render(<CommunityPage />);

    await waitFor(() => {
      expect(screen.getByText("Joined")).toBeInTheDocument();
    });

    expect(screen.getByText("Mod Panel")).toBeInTheDocument();
  });

  it("calls join API on join button click", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });
    communitiesApi.listJoined.mockResolvedValue({ data: [] });
    communitiesApi.getPosts.mockResolvedValue({ data: [] });
    communitiesApi.join.mockResolvedValue({});

    render(<CommunityPage />);

    await waitFor(() => {
      expect(screen.getByText("Join")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Join"));

    await waitFor(() => {
      expect(communitiesApi.join).toHaveBeenCalledWith("tech");
    });
  });

  it("shows empty state when no posts", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });
    communitiesApi.listJoined.mockResolvedValue({ data: [] });
    communitiesApi.getPosts.mockResolvedValue({ data: [] });

    render(<CommunityPage />);

    await waitFor(() => {
      expect(
        screen.getByText("No posts in this community yet."),
      ).toBeInTheDocument();
    });
  });
});
