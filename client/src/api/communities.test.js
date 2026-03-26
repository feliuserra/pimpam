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
  listJoined,
  create,
  get,
  getPosts,
  join,
  leave,
  getMemberKarma,
} from "./communities";

describe("communities API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET /communities with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await list({ sort: "popular", limit: 20 });
    expect(client.get).toHaveBeenCalledWith("/communities", {
      params: { sort: "popular", limit: 20 },
    });
  });

  it("listJoined calls GET /communities/joined", async () => {
    client.get.mockResolvedValue({ data: [] });
    await listJoined();
    expect(client.get).toHaveBeenCalledWith("/communities/joined");
  });

  it("create calls POST /communities", async () => {
    const data = { name: "tech", description: "Tech talk" };
    client.post.mockResolvedValue({ data: {} });
    await create(data);
    expect(client.post).toHaveBeenCalledWith("/communities", data);
  });

  it("get calls GET /communities/:name", async () => {
    client.get.mockResolvedValue({ data: {} });
    await get("music");
    expect(client.get).toHaveBeenCalledWith("/communities/music");
  });

  it("getPosts calls GET /communities/:name/posts with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getPosts("design", { cursor: "xyz" });
    expect(client.get).toHaveBeenCalledWith("/communities/design/posts", {
      params: { cursor: "xyz" },
    });
  });

  it("join calls POST /communities/:name/join", async () => {
    client.post.mockResolvedValue({ data: {} });
    await join("cooking");
    expect(client.post).toHaveBeenCalledWith("/communities/cooking/join");
  });

  it("leave calls POST /communities/:name/leave", async () => {
    client.post.mockResolvedValue({ data: {} });
    await leave("cooking");
    expect(client.post).toHaveBeenCalledWith("/communities/cooking/leave");
  });

  it("getMemberKarma calls GET /communities/:name/members/:username/karma", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getMemberKarma("tech", "alice");
    expect(client.get).toHaveBeenCalledWith(
      "/communities/tech/members/alice/karma",
    );
  });
});
