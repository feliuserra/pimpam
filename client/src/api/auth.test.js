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
  login,
  register,
  refresh,
  logout,
  changePassword,
  requestPasswordReset,
  confirmPasswordReset,
  verifyEmail,
  resendVerification,
  totpSetup,
  totpVerify,
  totpDisable,
} from "./auth";

describe("auth API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("login calls POST /auth/login with lowercase username", async () => {
    client.post.mockResolvedValue({ data: {} });
    await login("Alice", "pass123");
    expect(client.post).toHaveBeenCalledWith("/auth/login", {
      username: "alice",
      password: "pass123",
    });
  });

  it("login includes totp_code when provided", async () => {
    client.post.mockResolvedValue({ data: {} });
    await login("bob", "pass", "123456");
    expect(client.post).toHaveBeenCalledWith("/auth/login", {
      username: "bob",
      password: "pass",
      totp_code: "123456",
    });
  });

  it("login omits totp_code when falsy", async () => {
    client.post.mockResolvedValue({ data: {} });
    await login("bob", "pass", "");
    expect(client.post).toHaveBeenCalledWith("/auth/login", {
      username: "bob",
      password: "pass",
    });
  });

  it("register calls POST /auth/register", async () => {
    const data = { username: "new", email: "a@b.c", password: "p" };
    client.post.mockResolvedValue({ data: {} });
    await register(data);
    expect(client.post).toHaveBeenCalledWith("/auth/register", data);
  });

  it("refresh calls POST /auth/refresh", async () => {
    client.post.mockResolvedValue({ data: {} });
    await refresh("token-abc");
    expect(client.post).toHaveBeenCalledWith("/auth/refresh", {
      refresh_token: "token-abc",
    });
  });

  it("logout calls POST /auth/logout", async () => {
    client.post.mockResolvedValue({ data: {} });
    await logout();
    expect(client.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("changePassword calls POST /auth/change-password", async () => {
    const data = { current_password: "old", new_password: "new" };
    client.post.mockResolvedValue({ data: {} });
    await changePassword(data);
    expect(client.post).toHaveBeenCalledWith("/auth/change-password", data);
  });

  it("requestPasswordReset calls POST with default mode link", async () => {
    client.post.mockResolvedValue({ data: {} });
    await requestPasswordReset("a@b.c");
    expect(client.post).toHaveBeenCalledWith("/auth/password-reset/request", {
      email: "a@b.c",
      mode: "link",
    });
  });

  it("requestPasswordReset calls POST with custom mode", async () => {
    client.post.mockResolvedValue({ data: {} });
    await requestPasswordReset("a@b.c", "code");
    expect(client.post).toHaveBeenCalledWith("/auth/password-reset/request", {
      email: "a@b.c",
      mode: "code",
    });
  });

  it("confirmPasswordReset calls POST /auth/password-reset/confirm", async () => {
    client.post.mockResolvedValue({ data: {} });
    await confirmPasswordReset("tok", "newpw");
    expect(client.post).toHaveBeenCalledWith("/auth/password-reset/confirm", {
      token: "tok",
      new_password: "newpw",
    });
  });

  it("verifyEmail calls GET /auth/verify with token param", async () => {
    client.get.mockResolvedValue({ data: {} });
    await verifyEmail("my-token");
    expect(client.get).toHaveBeenCalledWith("/auth/verify?token=my-token");
  });

  it("resendVerification calls POST /auth/resend-verification", async () => {
    client.post.mockResolvedValue({ data: {} });
    await resendVerification();
    expect(client.post).toHaveBeenCalledWith("/auth/resend-verification");
  });

  it("totpSetup calls POST /auth/totp/setup", async () => {
    client.post.mockResolvedValue({ data: {} });
    await totpSetup();
    expect(client.post).toHaveBeenCalledWith("/auth/totp/setup");
  });

  it("totpVerify calls POST /auth/totp/verify with code", async () => {
    client.post.mockResolvedValue({ data: {} });
    await totpVerify("654321");
    expect(client.post).toHaveBeenCalledWith("/auth/totp/verify", {
      code: "654321",
    });
  });

  it("totpDisable calls POST /auth/totp/disable with password and code", async () => {
    client.post.mockResolvedValue({ data: {} });
    await totpDisable("mypass", "123456");
    expect(client.post).toHaveBeenCalledWith("/auth/totp/disable", {
      password: "mypass",
      code: "123456",
    });
  });
});
