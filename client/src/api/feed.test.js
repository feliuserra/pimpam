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
import { getFeed, getTrending, getNews } from "./feed";

describe("feed API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("getFeed calls GET /feed with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getFeed({ cursor: "abc" });
    expect(client.get).toHaveBeenCalledWith("/feed", {
      params: { cursor: "abc" },
    });
  });

  it("getFeed works without params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getFeed();
    expect(client.get).toHaveBeenCalledWith("/feed", {
      params: undefined,
    });
  });

  it("getTrending calls GET /feed/trending with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getTrending({ limit: 10 });
    expect(client.get).toHaveBeenCalledWith("/feed/trending", {
      params: { limit: 10 },
    });
  });

  it("getNews calls GET /feed/news with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getNews({ cursor: "xyz" });
    expect(client.get).toHaveBeenCalledWith("/feed/news", {
      params: { cursor: "xyz" },
    });
  });
});
