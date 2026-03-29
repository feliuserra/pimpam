/**
 * Passphrase-based key derivation and wrapping using Argon2id.
 *
 * Uses hash-wasm for memory-hard KDF, then AES-256-GCM
 * via Web Crypto for encrypting/decrypting the private key material.
 */

import { argon2id } from "hash-wasm";

const KDF_PARAMS = {
  memorySize: 65536, // 64 MB
  iterations: 3,
  parallelism: 1,
  hashLength: 32, // 256-bit key
};

/**
 * Derive an AES-256-GCM CryptoKey from a passphrase and salt using Argon2id.
 * @param {string} passphrase
 * @param {Uint8Array} salt — 16 bytes
 * @returns {Promise<CryptoKey>}
 */
export async function deriveKey(passphrase, salt) {
  const hash = await argon2id({
    password: passphrase,
    salt,
    ...KDF_PARAMS,
    outputType: "binary",
  });
  return crypto.subtle.importKey(
    "raw",
    hash,
    { name: "AES-GCM" },
    false,
    ["encrypt", "decrypt"],
  );
}

/**
 * Encrypt a PKCS8 private key with a derived AES-GCM key.
 * Returns combined [12-byte IV][ciphertext] as Uint8Array.
 * @param {ArrayBuffer} pkcs8Bytes
 * @param {CryptoKey} derivedKey
 * @returns {Promise<Uint8Array>}
 */
export async function wrapPrivateKey(pkcs8Bytes, derivedKey) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    derivedKey,
    pkcs8Bytes,
  );
  const combined = new Uint8Array(12 + encrypted.byteLength);
  combined.set(iv);
  combined.set(new Uint8Array(encrypted), 12);
  return combined;
}

/**
 * Decrypt a wrapped private key using a derived AES-GCM key.
 * @param {Uint8Array} wrappedBytes — [12-byte IV][ciphertext]
 * @param {CryptoKey} derivedKey
 * @returns {Promise<ArrayBuffer>} — PKCS8 bytes
 */
export async function unwrapPrivateKey(wrappedBytes, derivedKey) {
  const iv = wrappedBytes.slice(0, 12);
  const ciphertext = wrappedBytes.slice(12);
  return crypto.subtle.decrypt({ name: "AES-GCM", iv }, derivedKey, ciphertext);
}

/** Returns the KDF params as a JSON string for server storage. */
export function getKdfParamsJson() {
  return JSON.stringify({
    memory: KDF_PARAMS.memorySize,
    iterations: KDF_PARAMS.iterations,
    parallelism: KDF_PARAMS.parallelism,
  });
}
