/**
 * E2EE decryption — unwrap AES key with own RSA-OAEP private key, then AES-GCM decrypt.
 */

import { loadPrivateKey } from "./keys";

/**
 * Decode a base64 string to Uint8Array.
 */
function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Decrypt a message using the local private key.
 * @param {string} ciphertextBase64 — base64-encoded [IV + AES-GCM ciphertext]
 * @param {string} encryptedKeyBase64 — base64-encoded RSA-OAEP wrapped AES key
 * @returns {Promise<string>} — plaintext, or throws on failure
 */
export async function decryptMessage(ciphertextBase64, encryptedKeyBase64) {
  const privateKey = await loadPrivateKey();
  if (!privateKey) {
    throw new Error("No private key available — cannot decrypt");
  }

  // Unwrap the AES key
  const wrappedKey = base64ToBytes(encryptedKeyBase64);
  const rawAesKey = await crypto.subtle.decrypt(
    { name: "RSA-OAEP" },
    privateKey,
    wrappedKey,
  );

  // Import the unwrapped AES key
  const aesKey = await crypto.subtle.importKey(
    "raw",
    rawAesKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"],
  );

  // Split IV and ciphertext
  const combined = base64ToBytes(ciphertextBase64);
  const iv = combined.slice(0, 12);
  const ciphertext = combined.slice(12);

  // Decrypt
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv },
    aesKey,
    ciphertext,
  );

  return new TextDecoder().decode(decrypted);
}
