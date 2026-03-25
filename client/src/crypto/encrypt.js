/**
 * E2EE encryption — AES-256-GCM + RSA-OAEP key wrapping.
 *
 * For each message:
 * 1. Generate a random AES-256-GCM key
 * 2. Encrypt the plaintext with AES-GCM (random IV)
 * 3. Wrap (encrypt) the AES key with the recipient's RSA-OAEP public key
 * 4. Return { ciphertext, encryptedKey } as base64 strings
 */

import { importPublicKey } from "./keys";

/**
 * Encrypt a message for the given recipient.
 * @param {string} plaintext — the message text
 * @param {string} recipientPublicKeyBase64 — recipient's SPKI public key (base64)
 * @param {string} [senderPublicKeyBase64] — sender's own SPKI public key (base64),
 *   if provided the AES key is also wrapped for the sender so they can re-read the message.
 * @returns {Promise<{ciphertext: string, encryptedKey: string, senderEncryptedKey: string|null}>}
 */
export async function encryptMessage(plaintext, recipientPublicKeyBase64, senderPublicKeyBase64) {
  // Generate a one-time AES-256-GCM key
  const aesKey = await crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true, // extractable so we can wrap it
    ["encrypt"],
  );

  // Encrypt plaintext with AES-GCM
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(plaintext);
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    aesKey,
    encoded,
  );

  // Prepend IV to ciphertext: [12-byte IV][ciphertext]
  const combined = new Uint8Array(iv.length + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), iv.length);

  // Wrap AES key with recipient's RSA-OAEP public key
  const recipientKey = await importPublicKey(recipientPublicKeyBase64);
  const rawAesKey = await crypto.subtle.exportKey("raw", aesKey);
  const wrappedKey = await crypto.subtle.encrypt(
    { name: "RSA-OAEP" },
    recipientKey,
    rawAesKey,
  );

  // Optionally wrap AES key with sender's own public key
  let senderEncryptedKey = null;
  if (senderPublicKeyBase64) {
    const senderKey = await importPublicKey(senderPublicKeyBase64);
    const senderWrapped = await crypto.subtle.encrypt(
      { name: "RSA-OAEP" },
      senderKey,
      rawAesKey,
    );
    senderEncryptedKey = btoa(String.fromCharCode(...new Uint8Array(senderWrapped)));
  }

  return {
    ciphertext: btoa(String.fromCharCode(...combined)),
    encryptedKey: btoa(String.fromCharCode(...new Uint8Array(wrappedKey))),
    senderEncryptedKey,
  };
}
