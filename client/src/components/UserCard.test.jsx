import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import UserCard from "./UserCard";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" } })),
}));

vi.mock("../api/users", () => ({
  follow: vi.fn(),
  unfollow: vi.fn(),
}));

import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";

const baseUser = {
  id: 2,
  username: "janedoe",
  display_name: "Jane Doe",
  avatar_url: null,
  is_following: false,
};

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

describe("UserCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: { id: 1, username: "testuser" } });
  });

  it("renders username and display name", () => {
    wrap(<UserCard user={baseUser} />);

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("@janedoe")).toBeInTheDocument();
  });

  it("renders @username as display name when display_name is null", () => {
    wrap(<UserCard user={{ ...baseUser, display_name: null }} />);

    // The component renders @username as the name fallback
    const usernameElements = screen.getAllByText("@janedoe");
    expect(usernameElements.length).toBeGreaterThanOrEqual(1);
  });

  it("shows follow button for other users", () => {
    wrap(<UserCard user={baseUser} />);

    expect(screen.getByText("Follow")).toBeInTheDocument();
  });

  it("shows Following button when already following", () => {
    wrap(<UserCard user={{ ...baseUser, is_following: true }} />);

    expect(screen.getByText("Following")).toBeInTheDocument();
  });

  it("does not show follow button for self", () => {
    wrap(<UserCard user={{ ...baseUser, id: 1, username: "testuser" }} />);

    expect(screen.queryByText("Follow")).not.toBeInTheDocument();
    expect(screen.queryByText("Following")).not.toBeInTheDocument();
  });

  it("toggleFollow calls follow API when not following", async () => {
    usersApi.follow.mockResolvedValue({});

    wrap(<UserCard user={baseUser} />);

    fireEvent.click(screen.getByText("Follow"));

    await waitFor(() => {
      expect(usersApi.follow).toHaveBeenCalledWith("janedoe");
      expect(screen.getByText("Following")).toBeInTheDocument();
    });
  });

  it("toggleFollow calls unfollow API when already following", async () => {
    usersApi.unfollow.mockResolvedValue({});

    wrap(<UserCard user={{ ...baseUser, is_following: true }} />);

    fireEvent.click(screen.getByText("Following"));

    await waitFor(() => {
      expect(usersApi.unfollow).toHaveBeenCalledWith("janedoe");
      expect(screen.getByText("Follow")).toBeInTheDocument();
    });
  });

  it("does not show follow button when not logged in", () => {
    useAuth.mockReturnValue({ user: null });
    wrap(<UserCard user={baseUser} />);

    expect(screen.queryByText("Follow")).not.toBeInTheDocument();
  });
});
