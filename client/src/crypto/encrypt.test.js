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

    // importPublicKey returns different keys for recipient vs sender
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
    await encryptMessage("hello", "recipient-pub-b64");

    expect(crypto.subtle.generateKey).toHaveBeenCalledWith(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt"],
    );
  });

  it("encrypts plaintext with AES-GCM and a 12-byte IV", async () => {
    await encryptMessage("hello", "recipient-pub-b64");

    const aesCall = crypto.subtle.encrypt.mock.calls.find(
      (c) => c[0].name === "AES-GCM",
    );
    expect(aesCall).toBeTruthy();
    expect(aesCall[0].iv).toHaveLength(12);
    expect(aesCall[1]).toBe(mockAesKey);
  });

  it("wraps AES key with recipient RSA-OAEP public key", async () => {
    await encryptMessage("hello", "recipient-pub-b64");

    expect(importPublicKey).toHaveBeenCalledWith("recipient-pub-b64");
    const rsaCall = crypto.subtle.encrypt.mock.calls.find(
      (c) => c[0].name === "RSA-OAEP" && c[1] === mockRecipientKey,
    );
    expect(rsaCall).toBeTruthy();
  });

  it("returns ciphertext and encryptedKey as base64", async () => {
    const result = await encryptMessage("hello", "recipient-pub-b64");

    expect(typeof result.ciphertext).toBe("string");
    expect(typeof result.encryptedKey).toBe("string");
    // Verify they are valid base64 by decoding
    expect(() => atob(result.ciphertext)).not.toThrow();
    expect(() => atob(result.encryptedKey)).not.toThrow();
  });

  it("returns senderEncryptedKey as null when no sender key provided", async () => {
    const result = await encryptMessage("hello", "recipient-pub-b64");

    expect(result.senderEncryptedKey).toBeNull();
  });

  it("wraps AES key for sender when senderPublicKeyBase64 is provided", async () => {
    const result = await encryptMessage(
      "hello",
      "recipient-pub-b64",
      "sender-pub-b64",
    );

    expect(importPublicKey).toHaveBeenCalledWith("sender-pub-b64");
    const senderRsaCall = crypto.subtle.encrypt.mock.calls.find(
      (c) => c[0].name === "RSA-OAEP" && c[1] === mockSenderKey,
    );
    expect(senderRsaCall).toBeTruthy();
    expect(result.senderEncryptedKey).toBeTruthy();
    expect(typeof result.senderEncryptedKey).toBe("string");
    expect(() => atob(result.senderEncryptedKey)).not.toThrow();
  });

  it("prepends IV to ciphertext before base64-encoding", async () => {
    const result = await encryptMessage("hello", "recipient-pub-b64");

    // Decode the ciphertext
    const decoded = atob(result.ciphertext);
    // First 12 bytes should be the IV (0,1,2,...,11 from our mock getRandomValues)
    for (let i = 0; i < 12; i++) {
      expect(decoded.charCodeAt(i)).toBe(i);
    }
  });

  it("exports the raw AES key for wrapping", async () => {
    await encryptMessage("hello", "recipient-pub-b64");

    expect(crypto.subtle.exportKey).toHaveBeenCalledWith("raw", mockAesKey);
  });
});
