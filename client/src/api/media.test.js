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
import { upload } from "./media";

describe("media API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("upload sends POST /media/upload with FormData and correct media_type", async () => {
    client.post.mockResolvedValue({ data: { url: "https://cdn/img.webp" } });

    const fakeFile = new File(["pixels"], "photo.png", { type: "image/png" });
    await upload(fakeFile, "avatar");

    expect(client.post).toHaveBeenCalledTimes(1);
    const [url, body, config] = client.post.mock.calls[0];
    expect(url).toBe("/media/upload?media_type=avatar");
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("file")).toBe(fakeFile);
    expect(config).toEqual({ headers: { "Content-Type": undefined } });
  });

  it("upload passes different media_type values", async () => {
    client.post.mockResolvedValue({ data: {} });
    const fakeFile = new File(["data"], "pic.jpg", { type: "image/jpeg" });
    await upload(fakeFile, "post_image");

    const [url] = client.post.mock.calls[0];
    expect(url).toBe("/media/upload?media_type=post_image");
  });
});
