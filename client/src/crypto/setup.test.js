import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock dependencies
vi.mock("./keys", () => ({
  loadPrivateKey: vi.fn(),
  generateKeyPair: vi.fn(),
  storePrivateKey: vi.fn(),
  exportPublicKey: vi.fn(),
}));

vi.mock("../api/users", () => ({
  updateMe: vi.fn(),
}));

import {
  loadPrivateKey,
  generateKeyPair,
  storePrivateKey,
  exportPublicKey,
} from "./keys";
import { updateMe } from "../api/users";
import { ensureKeysExist } from "./setup";

describe("crypto/setup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns false when a private key already exists", async () => {
    loadPrivateKey.mockResolvedValue({ type: "private" });

    const result = await ensureKeysExist();

    expect(result).toBe(false);
    expect(generateKeyPair).not.toHaveBeenCalled();
    expect(storePrivateKey).not.toHaveBeenCalled();
    expect(updateMe).not.toHaveBeenCalled();
  });

  it("generates a new keypair when no private key exists", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private" },
    };
    loadPrivateKey.mockResolvedValue(null);
    generateKeyPair.mockResolvedValue(mockKeyPair);
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("base64-public-key");
    updateMe.mockResolvedValue({ data: {} });

    const result = await ensureKeysExist();

    expect(result).toBe(true);
    expect(generateKeyPair).toHaveBeenCalled();
  });

  it("stores the private key in IndexedDB", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private", id: "new" },
    };
    loadPrivateKey.mockResolvedValue(null);
    generateKeyPair.mockResolvedValue(mockKeyPair);
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("base64-public-key");
    updateMe.mockResolvedValue({ data: {} });

    await ensureKeysExist();

    expect(storePrivateKey).toHaveBeenCalledWith(mockKeyPair.privateKey);
  });

  it("publishes the public key to the server", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private" },
    };
    loadPrivateKey.mockResolvedValue(null);
    generateKeyPair.mockResolvedValue(mockKeyPair);
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("my-b64-key");
    updateMe.mockResolvedValue({ data: {} });

    await ensureKeysExist();

    expect(exportPublicKey).toHaveBeenCalledWith(mockKeyPair.publicKey);
    expect(updateMe).toHaveBeenCalledWith({
      e2ee_public_key: "my-b64-key",
    });
  });

  it("throws when key generation fails", async () => {
    loadPrivateKey.mockRejectedValue(new Error("IndexedDB error"));

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(ensureKeysExist()).rejects.toThrow("IndexedDB error");
    expect(consoleSpy).toHaveBeenCalledWith(
      "E2EE key setup failed:",
      expect.any(Error),
    );
    consoleSpy.mockRestore();
  });

  it("throws when storePrivateKey fails", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private" },
    };
    loadPrivateKey.mockResolvedValue(null);
    generateKeyPair.mockResolvedValue(mockKeyPair);
    storePrivateKey.mockRejectedValue(new Error("Storage full"));

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(ensureKeysExist()).rejects.toThrow("Storage full");
    consoleSpy.mockRestore();
  });

  it("throws when updateMe fails", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private" },
    };
    loadPrivateKey.mockResolvedValue(null);
    generateKeyPair.mockResolvedValue(mockKeyPair);
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("b64key");
    updateMe.mockRejectedValue(new Error("Network error"));

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    await expect(ensureKeysExist()).rejects.toThrow("Network error");
    consoleSpy.mockRestore();
  });
});
