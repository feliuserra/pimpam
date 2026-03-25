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
import { list, create, listReplies, remove, react, removeReaction } from "./comments";

describe("comments API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET /posts/:postId/comments with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await list(42, { sort: "top", cursor: "abc" });
    expect(client.get).toHaveBeenCalledWith("/posts/42/comments", {
      params: { sort: "top", cursor: "abc" },
    });
  });

  it("list works without params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await list(7, undefined);
    expect(client.get).toHaveBeenCalledWith("/posts/7/comments", {
      params: undefined,
    });
  });

  it("create calls POST /posts/:postId/comments", async () => {
    const data = { content: "Nice post!", parent_id: null };
    client.post.mockResolvedValue({ data: {} });
    await create(42, data);
    expect(client.post).toHaveBeenCalledWith("/posts/42/comments", data);
  });

  it("listReplies calls GET /comments/:commentId/replies", async () => {
    client.get.mockResolvedValue({ data: [] });
    await listReplies(99);
    expect(client.get).toHaveBeenCalledWith("/comments/99/replies");
  });

  it("remove calls DELETE /comments/:commentId", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await remove(55);
    expect(client.delete).toHaveBeenCalledWith("/comments/55");
  });

  it("react calls POST /comments/:commentId/reactions", async () => {
    client.post.mockResolvedValue({ data: {} });
    await react(10, "love");
    expect(client.post).toHaveBeenCalledWith("/comments/10/reactions", {
      reaction_type: "love",
    });
  });

  it("removeReaction calls DELETE /comments/:commentId/reactions/:type", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await removeReaction(10, "agree");
    expect(client.delete).toHaveBeenCalledWith("/comments/10/reactions/agree");
  });
});
