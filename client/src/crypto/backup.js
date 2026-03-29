/**
 * E2EE key backup — encrypt/decrypt a private key with a user passphrase.
 *
 * Uses Argon2id for key derivation and AES-256-GCM for wrapping.
 * The encrypted blob + salt + KDF params are stored server-side;
 * the passphrase never leaves the client.
 */

import { exportPrivateKeyPkcs8, storePrivateKey } from "./keys";
import { deriveKey, wrapPrivateKey, unwrapPrivateKey, getKdfParamsJson } from "./passphrase";

function bytesToBase64(bytes) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Create an encrypted backup of the private key.
 * @param {string} passphrase — user-chosen passphrase (min 12 chars recommended)
 * @param {CryptoKey} extractablePrivateKey — the extractable RSA-OAEP private key
 * @returns {Promise<{encrypted_private_key: string, salt: string, kdf: string, kdf_params: string}>}
 */
export async function createBackup(passphrase, extractablePrivateKey) {
  const pkcs8 = await exportPrivateKeyPkcs8(extractablePrivateKey);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const derivedKey = await deriveKey(passphrase, salt);
  const wrapped = await wrapPrivateKey(pkcs8, derivedKey);
  return {
    encrypted_private_key: bytesToBase64(wrapped),
    salt: bytesToBase64(salt),
    kdf: "argon2id",
    kdf_params: getKdfParamsJson(),
  };
}

/**
 * Restore a private key from an encrypted backup.
 * @param {{encrypted_private_key: string, salt: string}} backup — from server
 * @param {string} passphrase — user-entered passphrase
 * @returns {Promise<CryptoKey>} — the restored non-extractable private key, also stored in IndexedDB
 * @throws {Error} if passphrase is wrong (AES-GCM auth tag will fail)
 */
export async function restoreFromBackup(backup, passphrase) {
  const salt = base64ToBytes(backup.salt);
  const wrapped = base64ToBytes(backup.encrypted_private_key);
  const derivedKey = await deriveKey(passphrase, salt);
  const pkcs8 = await unwrapPrivateKey(wrapped, derivedKey);
  // Import as non-extractable RSA-OAEP private key
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    pkcs8,
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["decrypt"],
  );
  await storePrivateKey(privateKey);
  return privateKey;
}
