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
  removePost,
  restorePost,
  removeComment,
  restoreComment,
  proposeBan,
  voteBan,
  listBans,
  submitAppeal,
  voteAppeal,
  listAppeals,
  proposeMod,
  voteMod,
  proposeTransfer,
  respondTransfer,
} from "./moderation";

describe("moderation API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("removePost calls DELETE /communities/:name/posts/:postId", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await removePost("tech", 10);
    expect(client.delete).toHaveBeenCalledWith("/communities/tech/posts/10");
  });

  it("restorePost calls POST /communities/:name/posts/:postId/restore", async () => {
    client.post.mockResolvedValue({ data: {} });
    await restorePost("tech", 10);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/posts/10/restore",
    );
  });

  it("removeComment calls DELETE /communities/:name/comments/:commentId", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await removeComment("music", 33);
    expect(client.delete).toHaveBeenCalledWith(
      "/communities/music/comments/33",
    );
  });

  it("restoreComment calls POST /communities/:name/comments/:commentId/restore", async () => {
    client.post.mockResolvedValue({ data: {} });
    await restoreComment("music", 33);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/music/comments/33/restore",
    );
  });

  it("proposeBan calls POST /communities/:name/bans with data", async () => {
    const data = { target_id: 5, reason: "spam" };
    client.post.mockResolvedValue({ data: {} });
    await proposeBan("tech", data);
    expect(client.post).toHaveBeenCalledWith("/communities/tech/bans", data);
  });

  it("voteBan calls POST /communities/:name/bans/:proposalId/vote", async () => {
    client.post.mockResolvedValue({ data: {} });
    await voteBan("tech", 7);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/bans/7/vote",
    );
  });

  it("listBans calls GET /communities/:name/bans", async () => {
    client.get.mockResolvedValue({ data: [] });
    await listBans("tech");
    expect(client.get).toHaveBeenCalledWith("/communities/tech/bans");
  });

  it("submitAppeal calls POST /communities/:name/appeals with data", async () => {
    const data = { reason: "unfair" };
    client.post.mockResolvedValue({ data: {} });
    await submitAppeal("tech", data);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/appeals",
      data,
    );
  });

  it("voteAppeal calls POST /communities/:name/appeals/:appealId/vote", async () => {
    client.post.mockResolvedValue({ data: {} });
    await voteAppeal("tech", 3);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/appeals/3/vote",
    );
  });

  it("listAppeals calls GET /communities/:name/appeals", async () => {
    client.get.mockResolvedValue({ data: [] });
    await listAppeals("tech");
    expect(client.get).toHaveBeenCalledWith("/communities/tech/appeals");
  });

  it("proposeMod calls POST /communities/:name/moderators with data", async () => {
    const data = { target_id: 8, role: "moderator" };
    client.post.mockResolvedValue({ data: {} });
    await proposeMod("tech", data);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/moderators",
      data,
    );
  });

  it("voteMod calls POST /communities/:name/moderators/:proposalId/vote", async () => {
    client.post.mockResolvedValue({ data: {} });
    await voteMod("tech", 12);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/moderators/12/vote",
    );
  });

  it("proposeTransfer calls POST /communities/:name/ownership-transfer with data", async () => {
    const data = { target_id: 2 };
    client.post.mockResolvedValue({ data: {} });
    await proposeTransfer("tech", data);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/ownership-transfer",
      data,
    );
  });

  it("respondTransfer calls POST with accept=true", async () => {
    client.post.mockResolvedValue({ data: {} });
    await respondTransfer("tech", 4, true);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/ownership-transfer/4/respond",
      { accept: true },
    );
  });

  it("respondTransfer calls POST with accept=false", async () => {
    client.post.mockResolvedValue({ data: {} });
    await respondTransfer("tech", 4, false);
    expect(client.post).toHaveBeenCalledWith(
      "/communities/tech/ownership-transfer/4/respond",
      { accept: false },
    );
  });
});
