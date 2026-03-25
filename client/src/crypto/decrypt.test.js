import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock keys module to control loadPrivateKey
vi.mock("./keys", () => ({
  loadPrivateKey: vi.fn(),
}));

import { loadPrivateKey } from "./keys";
import { decryptMessage } from "./decrypt";

describe("crypto/decrypt", () => {
  let mockPrivateKey;
  let mockAesKey;

  beforeEach(() => {
    vi.clearAllMocks();

    mockPrivateKey = { type: "private", algorithm: "RSA-OAEP" };
    mockAesKey = { type: "secret", algorithm: "AES-GCM" };

    loadPrivateKey.mockResolvedValue(mockPrivateKey);

    const mockRawAesKey = new Uint8Array([50, 51, 52, 53]).buffer;
    const mockDecryptedContent = new TextEncoder().encode("hello world");

    vi.stubGlobal("crypto", {
      subtle: {
        decrypt: vi.fn().mockImplementation((algo) => {
          if (algo.name === "RSA-OAEP") {
            // Unwrapping the AES key
            return Promise.resolve(mockRawAesKey);
          }
          if (algo.name === "AES-GCM") {
            // Decrypting the message content
            return Promise.resolve(mockDecryptedContent.buffer);
          }
          return Promise.reject(new Error("Unknown algorithm"));
        }),
        importKey: vi.fn().mockResolvedValue(mockAesKey),
      },
    });
  });

  it("loads the private key from IndexedDB", async () => {
    // Create minimal valid base64 inputs
    // IV (12 bytes) + ciphertext (at least 1 byte) = 13+ bytes
    const fakeIVAndCiphertext = new Uint8Array(16);
    const ciphertextBase64 = btoa(String.fromCharCode(...fakeIVAndCiphertext));
    const encryptedKeyBase64 = btoa(String.fromCharCode(1, 2, 3));

    await decryptMessage(ciphertextBase64, encryptedKeyBase64);

    expect(loadPrivateKey).toHaveBeenCalled();
  });

  it("throws when no private key is available", async () => {
    loadPrivateKey.mockResolvedValue(null);

    const ciphertextBase64 = btoa("fake-data");
    const encryptedKeyBase64 = btoa("fake-key");

    await expect(
      decryptMessage(ciphertextBase64, encryptedKeyBase64),
    ).rejects.toThrow("No private key available");
  });

  it("unwraps the AES key using RSA-OAEP with private key", async () => {
    const fakeData = new Uint8Array(16);
    const ciphertextBase64 = btoa(String.fromCharCode(...fakeData));
    const wrappedKeyBytes = new Uint8Array([10, 20, 30]);
    const encryptedKeyBase64 = btoa(String.fromCharCode(...wrappedKeyBytes));

    await decryptMessage(ciphertextBase64, encryptedKeyBase64);

    // First decrypt call should be RSA-OAEP with the private key
    const rsaCall = crypto.subtle.decrypt.mock.calls.find(
      (c) => c[0].name === "RSA-OAEP",
    );
    expect(rsaCall).toBeTruthy();
    expect(rsaCall[1]).toBe(mockPrivateKey);
  });

  it("imports the unwrapped raw AES key", async () => {
    const fakeData = new Uint8Array(16);
    const ciphertextBase64 = btoa(String.fromCharCode(...fakeData));
    const encryptedKeyBase64 = btoa(String.fromCharCode(1, 2, 3));

    await decryptMessage(ciphertextBase64, encryptedKeyBase64);

    expect(crypto.subtle.importKey).toHaveBeenCalledWith(
      "raw",
      expect.any(ArrayBuffer),
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"],
    );
  });

  it("decrypts with AES-GCM using the first 12 bytes as IV", async () => {
    // Create known IV + ciphertext
    const iv = new Uint8Array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    const ct = new Uint8Array([99, 98, 97, 96]);
    const combined = new Uint8Array(iv.length + ct.length);
    combined.set(iv, 0);
    combined.set(ct, iv.length);

    const ciphertextBase64 = btoa(String.fromCharCode(...combined));
    const encryptedKeyBase64 = btoa(String.fromCharCode(1, 2, 3));

    await decryptMessage(ciphertextBase64, encryptedKeyBase64);

    const aesCall = crypto.subtle.decrypt.mock.calls.find(
      (c) => c[0].name === "AES-GCM",
    );
    expect(aesCall).toBeTruthy();
    // Verify IV is the first 12 bytes
    const usedIv = new Uint8Array(aesCall[0].iv);
    expect(usedIv).toEqual(iv);
    // Verify the ciphertext portion (bytes after IV)
    const usedCt = new Uint8Array(aesCall[2]);
    expect(usedCt).toEqual(ct);
  });

  it("returns the decrypted plaintext string", async () => {
    const fakeData = new Uint8Array(16);
    const ciphertextBase64 = btoa(String.fromCharCode(...fakeData));
    const encryptedKeyBase64 = btoa(String.fromCharCode(1, 2, 3));

    const result = await decryptMessage(ciphertextBase64, encryptedKeyBase64);

    expect(result).toBe("hello world");
  });
});
