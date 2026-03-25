import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";

// Mock API modules
vi.mock("../api/communities", () => ({
  list: vi.fn(),
  listJoined: vi.fn(),
}));

// Mock routing
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: vi.fn(() => vi.fn()),
    Link: ({ children, to }) => <a href={to}>{children}</a>,
  };
});

// Mock contexts — return a stable user reference to avoid re-triggering useEffect
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
vi.mock("../components/CommunityCard", () => ({
  default: ({ community }) => (
    <div data-testid="community-card">{community.name}</div>
  ),
}));
vi.mock("../components/CreateCommunityModal", () => ({
  default: ({ open, onClose }) =>
    open ? (
      <div data-testid="create-community-modal">
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

import * as communitiesApi from "../api/communities";
import Communities from "./Communities";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Communities", () => {
  const joinedCommunities = [
    { id: 1, name: "design" },
    { id: 2, name: "music" },
  ];

  const discoverCommunities = [
    { id: 3, name: "philosophy", member_count: 1200 },
    { id: 4, name: "cooking", member_count: 890 },
    { id: 5, name: "tech", member_count: 3400 },
  ];

  it("shows loading spinner", () => {
    communitiesApi.list.mockReturnValue(new Promise(() => {}));
    communitiesApi.listJoined.mockReturnValue(new Promise(() => {}));

    render(<Communities />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("renders joined communities as chips", async () => {
    communitiesApi.list.mockResolvedValue({ data: discoverCommunities });
    communitiesApi.listJoined.mockResolvedValue({ data: joinedCommunities });

    render(<Communities />);

    await waitFor(() => {
      expect(screen.getByText("c/design")).toBeInTheDocument();
    });

    expect(screen.getByText("c/music")).toBeInTheDocument();
    expect(screen.getByText("Your communities")).toBeInTheDocument();
  });

  it("renders discover communities list", async () => {
    // The useEffect fires and may be called multiple times in React 18 strict mode.
    // Use mockResolvedValue so every invocation resolves.
    communitiesApi.list.mockResolvedValue({ data: discoverCommunities });
    communitiesApi.listJoined.mockResolvedValue({ data: joinedCommunities });

    await act(async () => {
      render(<Communities />);
    });

    // After act completes, all microtasks (Promise.all, .then, .finally) should have flushed
    await waitFor(() => {
      expect(screen.getAllByTestId("community-card")).toHaveLength(3);
    });

    expect(screen.getByText("Discover")).toBeInTheDocument();
    expect(screen.getByText("philosophy")).toBeInTheDocument();
    expect(screen.getByText("cooking")).toBeInTheDocument();
    expect(screen.getByText("tech")).toBeInTheDocument();
  });

  it("'Create one' button opens modal when no joined communities", async () => {
    communitiesApi.list.mockResolvedValue({ data: discoverCommunities });
    communitiesApi.listJoined.mockResolvedValue({ data: [] });

    render(<Communities />);

    await waitFor(() => {
      expect(screen.getByText(/create one/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/create one/i));

    expect(screen.getByTestId("create-community-modal")).toBeInTheDocument();
  });

  it("'+ Create' chip opens modal when joined communities exist", async () => {
    communitiesApi.list.mockResolvedValue({ data: discoverCommunities });
    communitiesApi.listJoined.mockResolvedValue({ data: joinedCommunities });

    render(<Communities />);

    await waitFor(() => {
      expect(screen.getByText("+ Create")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("+ Create"));

    expect(screen.getByTestId("create-community-modal")).toBeInTheDocument();
  });

  it("sort toggle switches between popular/newest", async () => {
    communitiesApi.list.mockResolvedValue({ data: discoverCommunities });
    communitiesApi.listJoined.mockResolvedValue({ data: joinedCommunities });

    render(<Communities />);

    await waitFor(() => {
      expect(screen.getByText("Popular")).toBeInTheDocument();
    });

    // "Popular" is the default active sort
    expect(screen.getByText("Popular")).toBeInTheDocument();
    expect(screen.getByText("New")).toBeInTheDocument();

    // Click "New" to switch sort
    fireEvent.click(screen.getByText("New"));

    // Should re-fetch with new sort — list is called again
    await waitFor(() => {
      expect(communitiesApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ sort: "newest" }),
      );
    });
  });
});
