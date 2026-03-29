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
  send,
  getInbox,
  getConversation,
  getSingleMessage,
  deleteMessage,
  markRead,
} from "./messages";

describe("messages API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("send calls POST /messages with data", async () => {
    const data = { recipient_id: 5, ciphertext: "abc", device_keys: [] };
    client.post.mockResolvedValue({ data: {} });
    await send(data);
    expect(client.post).toHaveBeenCalledWith("/messages", data);
  });

  it("getInbox calls GET /messages with device_id", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getInbox(7);
    expect(client.get).toHaveBeenCalledWith("/messages", {
      params: { device_id: 7 },
    });
  });

  it("getInbox without device_id passes no params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getInbox();
    expect(client.get).toHaveBeenCalledWith("/messages", {
      params: undefined,
    });
  });

  it("getConversation calls GET /messages/:otherUserId with device_id", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getConversation(42, undefined, 7);
    expect(client.get).toHaveBeenCalledWith("/messages/42", {
      params: { device_id: 7 },
    });
  });

  it("getConversation with beforeId and device_id passes both params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getConversation(42, 100, 7);
    expect(client.get).toHaveBeenCalledWith("/messages/42", {
      params: { before_id: 100, device_id: 7 },
    });
  });

  it("getSingleMessage calls GET /messages/single/:id with device_id", async () => {
    client.get.mockResolvedValue({ data: {} });
    await getSingleMessage(99, 7);
    expect(client.get).toHaveBeenCalledWith("/messages/single/99", {
      params: { device_id: 7 },
    });
  });

  it("deleteMessage calls DELETE /messages/:id", async () => {
    client.delete.mockResolvedValue({ data: {} });
    await deleteMessage(99);
    expect(client.delete).toHaveBeenCalledWith("/messages/99");
  });

  it("markRead calls PATCH /messages/:otherUserId/read", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await markRead(42);
    expect(client.patch).toHaveBeenCalledWith("/messages/42/read");
  });
});
