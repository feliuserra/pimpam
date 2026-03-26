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
import { create, getFeed, getMine, remove, report } from "./stories";

describe("stories API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("create calls POST /stories with data", async () => {
    const data = { image_url: "https://cdn/img.webp", caption: "Sunset", duration_hours: 24 };
    client.post.mockResolvedValue({ data: {} });
    await create(data);
    expect(client.post).toHaveBeenCalledWith("/stories", data);
  });

  it("getFeed calls GET /stories/feed with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getFeed({ cursor: "abc" });
    expect(client.get).toHaveBeenCalledWith("/stories/feed", {
      params: { cursor: "abc" },
    });
  });

  it("getMine calls GET /stories/me", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getMine();
    expect(client.get).toHaveBeenCalledWith("/stories/me");
  });

  it("remove calls DELETE /stories/:id", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await remove(15);
    expect(client.delete).toHaveBeenCalledWith("/stories/15");
  });

  it("report calls POST /stories/:id/report", async () => {
    client.post.mockResolvedValue({ data: {} });
    await report(15);
    expect(client.post).toHaveBeenCalledWith("/stories/15/report");
  });
});
