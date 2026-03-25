import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../api/communities", () => ({
  get: vi.fn(),
}));

// Mock routing
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: vi.fn(() => ({ name: "tech" })),
    useNavigate: vi.fn(() => mockNavigate),
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

// Mock child components
vi.mock("../components/Header", () => ({
  default: ({ left, right }) => (
    <header data-testid="header">
      {left}
      {right}
    </header>
  ),
}));
vi.mock("../components/ui/Spinner", () => ({
  default: () => <div role="status" aria-label="Loading">Loading...</div>,
}));
vi.mock("../components/mod/RemovedContent", () => ({
  default: ({ communityName }) => (
    <div data-testid="removed-content">Removed: {communityName}</div>
  ),
}));
vi.mock("../components/mod/BanSection", () => ({
  default: ({ communityName }) => (
    <div data-testid="ban-section">Bans: {communityName}</div>
  ),
}));
vi.mock("../components/mod/ModPromotion", () => ({
  default: ({ communityName }) => (
    <div data-testid="mod-promotion">Mods: {communityName}</div>
  ),
}));
vi.mock("../components/mod/OwnershipTransfer", () => ({
  default: ({ communityName }) => (
    <div data-testid="ownership-transfer">Transfer: {communityName}</div>
  ),
}));

import * as communitiesApi from "../api/communities";
import ModPanel from "./ModPanel";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ModPanel", () => {
  const community = {
    id: 10,
    name: "tech",
    description: "Tech community",
    member_count: 500,
  };

  it("shows spinner while loading", () => {
    communitiesApi.get.mockReturnValue(new Promise(() => {}));

    render(<ModPanel />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.getByText("Mod: c/tech")).toBeInTheDocument();
  });

  it("renders mod panel with tabs after loading", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });

    render(<ModPanel />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Removed" })).toBeInTheDocument();
    });

    expect(screen.getByRole("tab", { name: "Bans" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Moderators" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Transfer" })).toBeInTheDocument();
  });

  it("shows RemovedContent component on Removed tab by default", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });

    render(<ModPanel />);

    await waitFor(() => {
      expect(screen.getByTestId("removed-content")).toBeInTheDocument();
    });

    expect(screen.getByText("Removed: tech")).toBeInTheDocument();
  });

  it("switches to Bans tab", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });

    render(<ModPanel />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Bans" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("tab", { name: "Bans" }));

    expect(screen.getByTestId("ban-section")).toBeInTheDocument();
    expect(screen.getByText("Bans: tech")).toBeInTheDocument();
  });

  it("switches to Moderators tab", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });

    render(<ModPanel />);

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Moderators" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("tab", { name: "Moderators" }));

    expect(screen.getByTestId("mod-promotion")).toBeInTheDocument();
    expect(screen.getByText("Mods: tech")).toBeInTheDocument();
  });

  it("navigates back to community on fetch error", async () => {
    communitiesApi.get.mockRejectedValue(new Error("Forbidden"));

    render(<ModPanel />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/c/tech", { replace: true });
    });
  });

  it("renders back link to community page", async () => {
    communitiesApi.get.mockResolvedValue({ data: community });

    render(<ModPanel />);

    await waitFor(() => {
      expect(screen.getByText("Mod Panel")).toBeInTheDocument();
    });

    const backLink = screen.getByText("← c/tech");
    expect(backLink).toBeInTheDocument();
    expect(backLink.closest("a")).toHaveAttribute("href", "/c/tech");
  });
});
