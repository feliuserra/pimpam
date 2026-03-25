import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import CommunityCard from "./CommunityCard";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));

vi.mock("../api/communities", () => ({
  join: vi.fn(),
}));

import { useAuth } from "../contexts/AuthContext";
import * as communitiesApi from "../api/communities";

const baseCommunity = {
  id: 5,
  name: "tech",
  description: "All things technology",
  member_count: 1234,
};

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("CommunityCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
  });

  it("renders community name, description, and member count", () => {
    wrap(<CommunityCard community={baseCommunity} />);

    expect(screen.getByText("c/tech")).toBeInTheDocument();
    expect(screen.getByText("All things technology")).toBeInTheDocument();
    // toLocaleString() output varies by environment; match flexibly
    expect(screen.getByText(/1,?234 members/)).toBeInTheDocument();
  });

  it("renders community without description", () => {
    wrap(
      <CommunityCard
        community={{ ...baseCommunity, description: null }}
      />,
    );

    expect(screen.getByText("c/tech")).toBeInTheDocument();
    expect(screen.getByText(/1,?234 members/)).toBeInTheDocument();
  });

  it("shows join button when user is logged in", () => {
    wrap(<CommunityCard community={baseCommunity} />);

    expect(screen.getByText("+")).toBeInTheDocument();
  });

  it("does not show join button when not logged in", () => {
    useAuth.mockReturnValue({ user: null });
    wrap(<CommunityCard community={baseCommunity} />);

    expect(screen.queryByText("+")).not.toBeInTheDocument();
  });

  it("calls join API on button click", async () => {
    communitiesApi.join.mockResolvedValue({});
    const onJoinChange = vi.fn();

    wrap(
      <CommunityCard community={baseCommunity} onJoinChange={onJoinChange} />,
    );

    fireEvent.click(screen.getByText("+"));

    await waitFor(() => {
      expect(communitiesApi.join).toHaveBeenCalledWith("tech");
      expect(onJoinChange).toHaveBeenCalledWith(5, true);
    });
  });

  it("links to community page", () => {
    wrap(<CommunityCard community={baseCommunity} />);

    const link = screen.getByText("c/tech").closest("a");
    expect(link).toHaveAttribute("href", "/c/tech");
  });
});
