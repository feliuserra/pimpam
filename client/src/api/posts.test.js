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
  create,
  get,
  edit,
  remove,
  vote,
  retractVote,
  boost,
  share,
  getLinkPreview,
} from "./posts";

describe("posts API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("create calls POST /posts with data", async () => {
    const data = { title: "Hello", content: "World" };
    client.post.mockResolvedValue({ data: {} });
    await create(data);
    expect(client.post).toHaveBeenCalledWith("/posts", data);
  });

  it("get calls GET /posts/:id", async () => {
    client.get.mockResolvedValue({ data: {} });
    await get(99);
    expect(client.get).toHaveBeenCalledWith("/posts/99");
  });

  it("edit calls PATCH /posts/:id with data", async () => {
    const data = { content: "Updated" };
    client.patch.mockResolvedValue({ data: {} });
    await edit(99, data);
    expect(client.patch).toHaveBeenCalledWith("/posts/99", data);
  });

  it("remove calls DELETE /posts/:id", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await remove(99);
    expect(client.delete).toHaveBeenCalledWith("/posts/99");
  });

  it("vote calls POST /posts/:id/vote with direction", async () => {
    client.post.mockResolvedValue({ data: {} });
    await vote(99, "up");
    expect(client.post).toHaveBeenCalledWith("/posts/99/vote", {
      direction: "up",
    });
  });

  it("vote handles down direction", async () => {
    client.post.mockResolvedValue({ data: {} });
    await vote(99, "down");
    expect(client.post).toHaveBeenCalledWith("/posts/99/vote", {
      direction: "down",
    });
  });

  it("retractVote calls DELETE /posts/:id/vote", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await retractVote(99);
    expect(client.delete).toHaveBeenCalledWith("/posts/99/vote");
  });

  it("boost calls POST /posts/:id/boost", async () => {
    client.post.mockResolvedValue({ data: {} });
    await boost(99);
    expect(client.post).toHaveBeenCalledWith("/posts/99/boost");
  });

  it("share calls POST /posts/:id/share with data", async () => {
    const data = { visibility: "followers" };
    client.post.mockResolvedValue({ data: {} });
    await share(99, data);
    expect(client.post).toHaveBeenCalledWith("/posts/99/share", data);
  });

  it("getLinkPreview calls GET /posts/link-preview with url param", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getLinkPreview("https://example.com");
    expect(client.get).toHaveBeenCalledWith("/posts/link-preview", {
      params: { url: "https://example.com" },
    });
  });
});
