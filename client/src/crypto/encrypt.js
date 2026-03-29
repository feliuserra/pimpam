/**
 * E2EE encryption — AES-256-GCM + RSA-OAEP key wrapping (multi-device).
 *
 * For each message:
 * 1. Generate a random AES-256-GCM key
 * 2. Encrypt the plaintext with AES-GCM (random IV)
 * 3. Wrap (encrypt) the AES key for each device of both sender and recipient
 * 4. Return { ciphertext, deviceKeys } as base64 strings
 */

import { importPublicKey } from "./keys";

/**
 * Encrypt a message for multiple devices.
 * @param {string} plaintext — the message text
 * @param {Array<{device_id: number, public_key: string}>} recipientDeviceKeys
 * @param {Array<{device_id: number, public_key: string}>} senderDeviceKeys
 * @returns {Promise<{ciphertext: string, deviceKeys: Array<{device_id: number, encrypted_key: string}>}>}
 */
export async function encryptMessage(
  plaintext,
  recipientDeviceKeys,
  senderDeviceKeys,
) {
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

  // Export raw AES key once
  const rawAesKey = await crypto.subtle.exportKey("raw", aesKey);

  // Wrap AES key for each device (both recipient + sender devices)
  const allDeviceKeys = [...recipientDeviceKeys, ...senderDeviceKeys];
  const deviceKeys = await Promise.all(
    allDeviceKeys.map(async (dk) => {
      const pubKey = await importPublicKey(dk.public_key);
      const wrapped = await crypto.subtle.encrypt(
        { name: "RSA-OAEP" },
        pubKey,
        rawAesKey,
      );
      return {
        device_id: dk.device_id,
        encrypted_key: btoa(String.fromCharCode(...new Uint8Array(wrapped))),
      };
    }),
  );

  return {
    ciphertext: btoa(String.fromCharCode(...combined)),
    deviceKeys,
  };
}
