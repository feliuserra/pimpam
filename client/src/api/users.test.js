import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import client from "./client";
import {
  getMe,
  updateMe,
  getUser,
  getUserPosts,
  getFollowers,
  getFollowing,
  follow,
  unfollow,
  deleteAccount,
  cancelDeletion,
  exportData,
  getSuggestions,
} from "./users";

describe("users API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("getMe calls GET /users/me", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getMe();
    expect(client.get).toHaveBeenCalledWith("/users/me");
  });

  it("updateMe calls PATCH /users/me with data", async () => {
    const data = { display_name: "Alice", bio: "Hello" };
    client.patch.mockResolvedValue({ data: {} });
    await updateMe(data);
    expect(client.patch).toHaveBeenCalledWith("/users/me", data);
  });

  it("getUser calls GET /users/:username", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getUser("alice");
    expect(client.get).toHaveBeenCalledWith("/users/alice");
  });

  it("getUserPosts calls GET /users/:username/posts with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getUserPosts("alice", { cursor: "c1" });
    expect(client.get).toHaveBeenCalledWith("/users/alice/posts", {
      params: { cursor: "c1" },
    });
  });

  it("getFollowers calls GET /users/:username/followers with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getFollowers("alice", { limit: 20 });
    expect(client.get).toHaveBeenCalledWith("/users/alice/followers", {
      params: { limit: 20 },
    });
  });

  it("getFollowing calls GET /users/:username/following with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getFollowing("alice", { limit: 10 });
    expect(client.get).toHaveBeenCalledWith("/users/alice/following", {
      params: { limit: 10 },
    });
  });

  it("follow calls POST /users/:username/follow", async () => {
    client.post.mockResolvedValue({ data: {} });
    await follow("bob");
    expect(client.post).toHaveBeenCalledWith("/users/bob/follow");
  });

  it("unfollow calls DELETE /users/:username/follow", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await unfollow("bob");
    expect(client.delete).toHaveBeenCalledWith("/users/bob/follow");
  });

  it("deleteAccount calls POST /users/me/delete with password", async () => {
    client.post.mockResolvedValue({ data: {} });
    await deleteAccount("mypassword");
    expect(client.post).toHaveBeenCalledWith("/users/me/delete", {
      password: "mypassword",
    });
  });

  it("cancelDeletion calls POST /users/me/delete/cancel", async () => {
    client.post.mockResolvedValue({ data: {} });
    await cancelDeletion();
    expect(client.post).toHaveBeenCalledWith("/users/me/delete/cancel");
  });

  it("exportData calls GET /users/me/data-export", async () => {
    client.get.mockResolvedValue({ data: {} });
    await exportData();
    expect(client.get).toHaveBeenCalledWith("/users/me/data-export");
  });

  it("getSuggestions calls GET /users/me/suggestions", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getSuggestions();
    expect(client.get).toHaveBeenCalledWith("/users/me/suggestions");
  });
});
