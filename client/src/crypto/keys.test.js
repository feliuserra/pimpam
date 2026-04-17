import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  generateKeyPair,
  exportPublicKey,
  importPublicKey,
  storePrivateKey,
  loadPrivateKey,
  computeFingerprint,
} from "./keys";

// --- IndexedDB mock ---
function createMockIndexedDB() {
  const stores = {};

  function mockOpen(name, version) {
    const isNew = !stores[name];
    const dbStore = stores[name] || (stores[name] = {});
    const result = {
      result: null,
      error: null,
      onupgradeneeded: null,
      onsuccess: null,
      onerror: null,
    };

    const db = {
      createObjectStore: (storeName) => {
        dbStore[storeName] = {};
      },
      transaction: (storeName, mode) => {
        const tx = {
          oncomplete: null,
          onerror: null,
          error: null,
          objectStore: (sName) => ({
            put: (value, key) => {
              if (!dbStore[sName]) dbStore[sName] = {};
              dbStore[sName][key] = value;
              // fire oncomplete asynchronously
              queueMicrotask(() => tx.oncomplete?.());
              return { onsuccess: null, onerror: null };
            },
            get: (key) => {
              const req = {
                result: dbStore[sName]?.[key] ?? undefined,
                error: null,
                onsuccess: null,
                onerror: null,
              };
              queueMicrotask(() => req.onsuccess?.());
              return req;
            },
          }),
        };
        return tx;
      },
    };

    result.result = db;

    queueMicrotask(() => {
      if (isNew) {
        result.onupgradeneeded?.();
      }
      result.onsuccess?.();
    });

    return result;
  }

  return { open: mockOpen, _stores: stores };
}

// --- crypto.subtle mock ---
function createMockCryptoSubtle() {
  const mockPublicKey = { type: "public", algorithm: "RSA-OAEP" };
  const mockPrivateKey = { type: "private", algorithm: "RSA-OAEP" };
  const mockKeyPair = { publicKey: mockPublicKey, privateKey: mockPrivateKey };
  const mockSpkiBytes = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);

  return {
    generateKey: vi.fn().mockResolvedValue(mockKeyPair),
    exportKey: vi.fn().mockResolvedValue(mockSpkiBytes.buffer),
    importKey: vi.fn().mockResolvedValue(mockPublicKey),
    encrypt: vi.fn(),
    decrypt: vi.fn(),
    mockKeyPair,
    mockSpkiBytes,
    mockPublicKey,
  };
}

describe("crypto/keys", () => {
  let mockSubtle;

  beforeEach(() => {
    vi.clearAllMocks();

    const mockIDB = createMockIndexedDB();
    vi.stubGlobal("indexedDB", mockIDB);

    mockSubtle = createMockCryptoSubtle();
    vi.stubGlobal("crypto", {
      subtle: mockSubtle,
      getRandomValues: (arr) => {
        for (let i = 0; i < arr.length; i++) arr[i] = i;
        return arr;
      },
    });
  });

  describe("generateKeyPair", () => {
    it("calls crypto.subtle.generateKey with RSA-OAEP 2048", async () => {
      const keyPair = await generateKeyPair();

      expect(mockSubtle.generateKey).toHaveBeenCalledWith(
        {
          name: "RSA-OAEP",
          modulusLength: 2048,
          publicExponent: new Uint8Array([1, 0, 1]),
          hash: "SHA-256",
        },
        false,
        ["encrypt", "decrypt"],
      );
      expect(keyPair).toBe(mockSubtle.mockKeyPair);
    });
  });

  describe("exportPublicKey", () => {
    it("exports a public key to base64 SPKI string", async () => {
      const base64 = await exportPublicKey(mockSubtle.mockPublicKey);

      expect(mockSubtle.exportKey).toHaveBeenCalledWith(
        "spki",
        mockSubtle.mockPublicKey,
      );
      // The mock returns bytes [1,2,3,4,5,6,7,8] — check base64 encoding
      const expected = btoa(
        String.fromCharCode(...mockSubtle.mockSpkiBytes),
      );
      expect(base64).toBe(expected);
    });
  });

  describe("importPublicKey", () => {
    it("imports a base64 SPKI string to a CryptoKey", async () => {
      const base64 = btoa(String.fromCharCode(1, 2, 3));
      const result = await importPublicKey(base64);

      expect(mockSubtle.importKey).toHaveBeenCalledWith(
        "spki",
        expect.any(ArrayBuffer),
        { name: "RSA-OAEP", hash: "SHA-256" },
        false,
        ["encrypt"],
      );
      expect(result).toBe(mockSubtle.mockPublicKey);
    });

    it("correctly decodes base64 to binary", async () => {
      const originalBytes = new Uint8Array([10, 20, 30, 40]);
      const base64 = btoa(String.fromCharCode(...originalBytes));
      await importPublicKey(base64);

      const passedBuffer = mockSubtle.importKey.mock.calls[0][1];
      const passedBytes = new Uint8Array(passedBuffer);
      expect(passedBytes).toEqual(originalBytes);
    });
  });

  describe("storePrivateKey / loadPrivateKey", () => {
    it("stores and retrieves a private key from IndexedDB", async () => {
      const fakeKey = { type: "private", mock: true };
      await storePrivateKey(fakeKey);
      const loaded = await loadPrivateKey();
      expect(loaded).toBe(fakeKey);
    });

    it("returns null when no key is stored", async () => {
      const loaded = await loadPrivateKey();
      expect(loaded).toBeNull();
    });
  });

  describe("computeFingerprint", () => {
    it("returns a 64-character hex SHA-256 digest", async () => {
      // Mock crypto.subtle.digest to return a known hash
      const fakeHash = new Uint8Array(32);
      for (let i = 0; i < 32; i++) fakeHash[i] = i;
      mockSubtle.digest = vi.fn().mockResolvedValue(fakeHash.buffer);

      const base64Input = btoa(String.fromCharCode(1, 2, 3));
      const result = await computeFingerprint(base64Input);

      expect(mockSubtle.digest).toHaveBeenCalledWith("SHA-256", expect.any(Uint8Array));
      expect(result).toHaveLength(64);
      expect(result).toMatch(/^[0-9a-f]{64}$/);
      // Verify the expected hex from our mock
      const expected = Array.from(fakeHash)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
      expect(result).toBe(expected);
    });
  });
});
