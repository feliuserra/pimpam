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
  list,
  create,
  getCloseFriends,
  getDetail,
  rename,
  remove,
  addMember,
  removeMember,
} from "./friendGroups";

describe("friendGroups API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET /friend-groups", async () => {
    client.get.mockResolvedValue({ data: [] });
    await list();
    expect(client.get).toHaveBeenCalledWith("/friend-groups");
  });

  it("create calls POST /friend-groups with name", async () => {
    client.post.mockResolvedValue({ data: {} });
    await create("Besties");
    expect(client.post).toHaveBeenCalledWith("/friend-groups", {
      name: "Besties",
    });
  });

  it("getCloseFriends calls GET /friend-groups/close-friends", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getCloseFriends();
    expect(client.get).toHaveBeenCalledWith("/friend-groups/close-friends");
  });

  it("getDetail calls GET /friend-groups/:id", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getDetail(5);
    expect(client.get).toHaveBeenCalledWith("/friend-groups/5");
  });

  it("rename calls PATCH /friend-groups/:id with new name", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await rename(5, "New Name");
    expect(client.patch).toHaveBeenCalledWith("/friend-groups/5", {
      name: "New Name",
    });
  });

  it("remove calls DELETE /friend-groups/:id", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await remove(5);
    expect(client.delete).toHaveBeenCalledWith("/friend-groups/5");
  });

  it("addMember calls POST /friend-groups/:id/members with user_id", async () => {
    client.post.mockResolvedValue({ data: {} });
    await addMember(5, 42);
    expect(client.post).toHaveBeenCalledWith("/friend-groups/5/members", {
      user_id: 42,
    });
  });

  it("removeMember calls DELETE /friend-groups/:id/members/:userId", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await removeMember(5, 42);
    expect(client.delete).toHaveBeenCalledWith("/friend-groups/5/members/42");
  });
});
