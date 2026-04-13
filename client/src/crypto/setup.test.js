import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./keys", () => ({
  loadPrivateKey: vi.fn(),
  loadDeviceId: vi.fn(),
  generateExtractableKeyPair: vi.fn(),
  reimportAsNonExtractable: vi.fn(),
  storePrivateKey: vi.fn(),
  storeDeviceId: vi.fn(),
  exportPublicKey: vi.fn(),
}));

vi.mock("../api/devices", () => ({
  registerDevice: vi.fn(),
  getMyDevices: vi.fn(),
  getAvailableBackups: vi.fn(),
}));

import {
  loadPrivateKey,
  loadDeviceId,
  generateExtractableKeyPair,
  reimportAsNonExtractable,
  storePrivateKey,
  storeDeviceId,
  exportPublicKey,
} from "./keys";
import { registerDevice, getMyDevices, getAvailableBackups } from "../api/devices";
import { ensureKeysExist } from "./setup";

describe("crypto/setup", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns existing device when key and device ID exist and device is active", async () => {
    loadPrivateKey.mockResolvedValue({ type: "private" });
    loadDeviceId.mockResolvedValue(42);
    getMyDevices.mockResolvedValue({ data: [{ id: 42 }] });

    const result = await ensureKeysExist();

    expect(result).toEqual({ isNewDevice: false, deviceId: 42 });
    expect(generateExtractableKeyPair).not.toHaveBeenCalled();
  });

  it("signals recovery when backup exists and no local key", async () => {
    loadPrivateKey.mockResolvedValue(null);
    loadDeviceId.mockResolvedValue(null);
    getAvailableBackups.mockResolvedValue({
      data: [{ device_id: 10 }],
    });

    const result = await ensureKeysExist();

    expect(result).toEqual({ needsRecovery: true, backupDeviceId: 10 });
  });

  it("generates new keypair and registers device when no key exists", async () => {
    const mockKeyPair = {
      publicKey: { type: "public" },
      privateKey: { type: "private", extractable: true },
    };
    const mockNonExtractable = { type: "private", extractable: false };

    loadPrivateKey.mockResolvedValue(null);
    loadDeviceId.mockResolvedValue(null);
    getAvailableBackups.mockResolvedValue({ data: [] });
    generateExtractableKeyPair.mockResolvedValue(mockKeyPair);
    reimportAsNonExtractable.mockResolvedValue(mockNonExtractable);
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("base64-public-key");
    registerDevice.mockResolvedValue({ data: { id: 99 } });
    storeDeviceId.mockResolvedValue(undefined);

    const result = await ensureKeysExist();

    expect(result.isNewDevice).toBe(true);
    expect(result.deviceId).toBe(99);
    expect(result.extractablePrivateKey).toBe(mockKeyPair.privateKey);
    expect(storePrivateKey).toHaveBeenCalledWith(mockNonExtractable);
    expect(registerDevice).toHaveBeenCalled();
    expect(storeDeviceId).toHaveBeenCalledWith(99);
  });

  it("returns gracefully when loadPrivateKey throws", async () => {
    loadPrivateKey.mockRejectedValue(new Error("IndexedDB error"));
    loadDeviceId.mockResolvedValue(null);

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const result = await ensureKeysExist();

    expect(result).toEqual({ isNewDevice: false, deviceId: null });
    expect(consoleSpy).toHaveBeenCalledWith(
      "E2EE key setup failed:",
      expect.any(Error),
    );
    consoleSpy.mockRestore();
  });

  it("returns gracefully when registerDevice fails", async () => {
    loadPrivateKey.mockResolvedValue(null);
    loadDeviceId.mockResolvedValue(null);
    getAvailableBackups.mockResolvedValue({ data: [] });
    generateExtractableKeyPair.mockResolvedValue({
      publicKey: { type: "public" },
      privateKey: { type: "private" },
    });
    reimportAsNonExtractable.mockResolvedValue({ type: "private" });
    storePrivateKey.mockResolvedValue(undefined);
    exportPublicKey.mockResolvedValue("key");
    registerDevice.mockRejectedValue(new Error("Network error"));

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const result = await ensureKeysExist();

    expect(result).toEqual({ isNewDevice: false, deviceId: null });
    consoleSpy.mockRestore();
  });
});
