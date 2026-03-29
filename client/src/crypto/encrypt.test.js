import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock keys module to control importPublicKey
vi.mock("./keys", () => ({
  importPublicKey: vi.fn(),
}));

import { importPublicKey } from "./keys";
import { encryptMessage } from "./encrypt";

describe("crypto/encrypt", () => {
  let mockAesKey;
  let mockRecipientKey;
  let mockSenderKey;

  beforeEach(() => {
    vi.clearAllMocks();

    mockAesKey = { type: "secret", extractable: true };
    mockRecipientKey = { type: "public", owner: "recipient" };
    mockSenderKey = { type: "public", owner: "sender" };

    importPublicKey.mockImplementation((base64) => {
      if (base64 === "recipient-pub-b64") return Promise.resolve(mockRecipientKey);
      if (base64 === "sender-pub-b64") return Promise.resolve(mockSenderKey);
      return Promise.resolve({ type: "public", owner: "unknown" });
    });

    const mockEncryptedContent = new Uint8Array([100, 101, 102, 103]);
    const mockRawAesKeyBytes = new Uint8Array([50, 51, 52, 53]);
    const mockWrappedKey = new Uint8Array([200, 201, 202]);
    const mockSenderWrappedKey = new Uint8Array([210, 211, 212]);

    vi.stubGlobal("crypto", {
      subtle: {
        generateKey: vi.fn().mockResolvedValue(mockAesKey),
        encrypt: vi.fn().mockImplementation((algo, key) => {
          if (algo.name === "AES-GCM") {
            return Promise.resolve(mockEncryptedContent.buffer);
          }
          // RSA-OAEP wrapping
          if (key === mockRecipientKey) {
            return Promise.resolve(mockWrappedKey.buffer);
          }
          if (key === mockSenderKey) {
            return Promise.resolve(mockSenderWrappedKey.buffer);
          }
          return Promise.resolve(new ArrayBuffer(0));
        }),
        exportKey: vi.fn().mockResolvedValue(mockRawAesKeyBytes.buffer),
      },
      getRandomValues: (arr) => {
        for (let i = 0; i < arr.length; i++) arr[i] = i;
        return arr;
      },
    });
  });

  it("generates an AES-256-GCM key", async () => {
    await encryptMessage("hello", [{ device_id: 1, public_key: "recipient-pub-b64" }], []);

    expect(crypto.subtle.generateKey).toHaveBeenCalledWith(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt"],
    );
  });

  it("encrypts plaintext with AES-GCM and a 12-byte IV", async () => {
    await encryptMessage("hello", [{ device_id: 1, public_key: "recipient-pub-b64" }], []);

    const aesCall = crypto.subtle.encrypt.mock.calls.find(
      (c) => c[0].name === "AES-GCM",
    );
    expect(aesCall).toBeTruthy();
    expect(aesCall[0].iv).toHaveLength(12);
    expect(aesCall[1]).toBe(mockAesKey);
  });

  it("wraps AES key with recipient device RSA-OAEP public key", async () => {
    await encryptMessage("hello", [{ device_id: 10, public_key: "recipient-pub-b64" }], []);

    expect(importPublicKey).toHaveBeenCalledWith("recipient-pub-b64");
    const rsaCall = crypto.subtle.encrypt.mock.calls.find(
      (c) => c[0].name === "RSA-OAEP" && c[1] === mockRecipientKey,
    );
    expect(rsaCall).toBeTruthy();
  });

  it("returns ciphertext and deviceKeys with base64 encrypted_key", async () => {
    const result = await encryptMessage(
      "hello",
      [{ device_id: 10, public_key: "recipient-pub-b64" }],
      [],
    );

    expect(typeof result.ciphertext).toBe("string");
    expect(() => atob(result.ciphertext)).not.toThrow();
    expect(result.deviceKeys).toHaveLength(1);
    expect(result.deviceKeys[0].device_id).toBe(10);
    expect(typeof result.deviceKeys[0].encrypted_key).toBe("string");
    expect(() => atob(result.deviceKeys[0].encrypted_key)).not.toThrow();
  });

  it("returns empty deviceKeys when no device keys provided", async () => {
    const result = await encryptMessage("hello", [], []);

    expect(result.deviceKeys).toEqual([]);
  });

  it("wraps AES key for both recipient and sender devices", async () => {
    const result = await encryptMessage(
      "hello",
      [{ device_id: 10, public_key: "recipient-pub-b64" }],
      [{ device_id: 20, public_key: "sender-pub-b64" }],
    );

    expect(importPublicKey).toHaveBeenCalledWith("recipient-pub-b64");
    expect(importPublicKey).toHaveBeenCalledWith("sender-pub-b64");
    expect(result.deviceKeys).toHaveLength(2);
    expect(result.deviceKeys[0].device_id).toBe(10);
    expect(result.deviceKeys[1].device_id).toBe(20);
    expect(() => atob(result.deviceKeys[1].encrypted_key)).not.toThrow();
  });

  it("prepends IV to ciphertext before base64-encoding", async () => {
    const result = await encryptMessage(
      "hello",
      [{ device_id: 1, public_key: "recipient-pub-b64" }],
      [],
    );

    // Decode the ciphertext
    const decoded = atob(result.ciphertext);
    // First 12 bytes should be the IV (0,1,2,...,11 from our mock getRandomValues)
    for (let i = 0; i < 12; i++) {
      expect(decoded.charCodeAt(i)).toBe(i);
    }
  });

  it("exports the raw AES key for wrapping", async () => {
    await encryptMessage("hello", [{ device_id: 1, public_key: "recipient-pub-b64" }], []);

    expect(crypto.subtle.exportKey).toHaveBeenCalledWith("raw", mockAesKey);
  });
});
