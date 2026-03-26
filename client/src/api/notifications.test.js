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
  getUnreadCount,
  markAllRead,
  markRead,
  getPreferences,
  updatePreference,
} from "./notifications";

describe("notifications API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("list calls GET /notifications with params", async () => {
    client.get.mockResolvedValue({ data: [] });
    await list({ cursor: "c1", limit: 20 });
    expect(client.get).toHaveBeenCalledWith("/notifications", {
      params: { cursor: "c1", limit: 20 },
    });
  });

  it("getUnreadCount calls GET /notifications/unread-count", async () => {
    client.get.mockResolvedValue({ data: { count: 5 } });
    await getUnreadCount();
    expect(client.get).toHaveBeenCalledWith("/notifications/unread-count");
  });

  it("markAllRead calls PATCH /notifications/read-all", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await markAllRead();
    expect(client.patch).toHaveBeenCalledWith("/notifications/read-all");
  });

  it("markRead calls PATCH /notifications/:id/read", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await markRead(77);
    expect(client.patch).toHaveBeenCalledWith("/notifications/77/read");
  });

  it("getPreferences calls GET /notifications/preferences", async () => {
    client.get.mockResolvedValue({ data: [] });
    await getPreferences();
    expect(client.get).toHaveBeenCalledWith("/notifications/preferences");
  });

  it("updatePreference calls PATCH /notifications/preferences", async () => {
    client.patch.mockResolvedValue({ data: {} });
    await updatePreference("new_comment", false);
    expect(client.patch).toHaveBeenCalledWith("/notifications/preferences", {
      notification_type: "new_comment",
      enabled: false,
    });
  });
});
