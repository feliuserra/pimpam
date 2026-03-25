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
import { send, getInbox, getConversation, markRead } from "./messages";

describe("messages API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("send calls POST /messages with data", async () => {
    const data = { recipient_id: 5, ciphertext: "abc", encrypted_key: "xyz" };
    client.post.mockResolvedValue({ data: {} });
    await send(data);
    expect(client.post).toHaveBeenCalledWith("/messages", data);
  });

  it("getInbox calls GET /messages", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getInbox();
    expect(client.get).toHaveBeenCalledWith("/messages");
  });

  it("getConversation calls GET /messages/:otherUserId", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getConversation(42);
    expect(client.get).toHaveBeenCalledWith("/messages/42");
  });

  it("markRead calls PATCH /messages/:otherUserId/read", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await markRead(42);
    expect(client.patch).toHaveBeenCalledWith("/messages/42/read");
  });
});
