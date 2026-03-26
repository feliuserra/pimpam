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
import { search } from "./search";

describe("search API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("search calls GET /search with params", async () => {
    client.get.mockResolvedValue({ data: { results: [] } });
    await search({ q: "hello", type: "posts" });
    expect(client.get).toHaveBeenCalledWith("/search", {
      params: { q: "hello", type: "posts" },
    });
  });

  it("search passes all params through", async () => {
    client.get.mockResolvedValue({ data: { results: [] } });
    await search({ q: "test", type: "users", limit: 10, offset: 5 });
    expect(client.get).toHaveBeenCalledWith("/search", {
      params: { q: "test", type: "users", limit: 10, offset: 5 },
    });
  });
});
