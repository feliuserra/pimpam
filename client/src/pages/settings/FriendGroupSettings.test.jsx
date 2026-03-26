import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock API modules
vi.mock("../../api/friendGroups", () => ({
  list: vi.fn(),
  create: vi.fn(),
  getDetail: vi.fn(),
  remove: vi.fn(),
  removeMember: vi.fn(),
}));

// Mock child components
vi.mock("../../components/ui/Spinner", () => ({
  default: () => <div role="status" aria-label="Loading">Loading...</div>,
}));

import * as friendGroupsApi from "../../api/friendGroups";
import FriendGroupSettings from "./FriendGroupSettings";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FriendGroupSettings", () => {
  const groups = [
    { id: 1, name: "Close Friends", is_close_friends: true, member_count: 3 },
    { id: 2, name: "Work Buddies", is_close_friends: false, member_count: 5 },
  ];

  it("shows spinner while loading", () => {
    friendGroupsApi.list.mockReturnValue(new Promise(() => {}));

    render(<FriendGroupSettings />);

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("renders group list after loading", async () => {
    friendGroupsApi.list.mockResolvedValue({ data: groups });

    render(<FriendGroupSettings />);

    await waitFor(() => {
      expect(screen.getByText("Work Buddies")).toBeInTheDocument();
    });

    expect(screen.getByText("5 members")).toBeInTheDocument();
    expect(screen.getByText("Friend Groups")).toBeInTheDocument();
  });

  it("shows empty state when no groups", async () => {
    friendGroupsApi.list.mockResolvedValue({ data: [] });

    render(<FriendGroupSettings />);

    await waitFor(() => {
      expect(screen.getByText("No friend groups yet.")).toBeInTheDocument();
    });
  });

  it("creates a new group via the form", async () => {
    friendGroupsApi.list.mockResolvedValue({ data: [] });
    friendGroupsApi.create.mockResolvedValue({});

    render(<FriendGroupSettings />);

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("New group name"),
      ).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("New group name"), {
      target: { value: "Gaming" },
    });
    fireEvent.click(screen.getByRole("button", { name: /create/i }));

    await waitFor(() => {
      expect(friendGroupsApi.create).toHaveBeenCalledWith("Gaming");
    });
  });

  it("does not show delete button for close friends group", async () => {
    friendGroupsApi.list.mockResolvedValue({
      data: [{ id: 1, name: "Close Friends", is_close_friends: true, member_count: 2 }],
    });

    render(<FriendGroupSettings />);

    // Wait for the member count text which only appears after loading
    await waitFor(() => {
      expect(screen.getByText(/2 member/)).toBeInTheDocument();
    });

    // No delete button for close friends
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("shows delete button for non-close-friends groups", async () => {
    friendGroupsApi.list.mockResolvedValue({
      data: [{ id: 2, name: "Work Buddies", is_close_friends: false, member_count: 1 }],
    });

    render(<FriendGroupSettings />);

    await waitFor(() => {
      expect(screen.getByText("Work Buddies")).toBeInTheDocument();
    });

    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("expands group to show members on click", async () => {
    const groupWithMembers = {
      id: 2,
      name: "Work Buddies",
      is_close_friends: false,
      member_count: 1,
      members: [{ user_id: 5, username: "alice" }],
    };
    friendGroupsApi.list.mockResolvedValue({
      data: [{ id: 2, name: "Work Buddies", is_close_friends: false, member_count: 1 }],
    });
    friendGroupsApi.getDetail.mockResolvedValue({ data: groupWithMembers });

    render(<FriendGroupSettings />);

    await waitFor(() => {
      expect(screen.getByText("Work Buddies")).toBeInTheDocument();
    });

    // Click group name to expand
    fireEvent.click(screen.getByText("Work Buddies"));

    await waitFor(() => {
      expect(screen.getByText("@alice")).toBeInTheDocument();
    });

    expect(screen.getByText("Remove")).toBeInTheDocument();
  });
});
