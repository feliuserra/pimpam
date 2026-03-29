import { decryptMessage } from "./decrypt";
import { loadDeviceId } from "./keys";

/**
 * Try to decrypt a message using this device's wrapped key.
 * Falls back to plaintext display or a placeholder.
 */
export async function tryDecrypt(msg) {
  // No device keys — message is plaintext (pre-E2EE) or has no encryption
  if (!msg.device_keys?.length) {
    return { ...msg, decryptedText: msg.ciphertext };
  }

  // Find this device's wrapped key
  const myDeviceId = await loadDeviceId();
  const myEntry = msg.device_keys.find((dk) => dk.device_id === myDeviceId);

  if (!myEntry) {
    return { ...msg, decryptedText: "[Cannot decrypt on this device]" };
  }

  try {
    const text = await decryptMessage(msg.ciphertext, myEntry.encrypted_key);
    return { ...msg, decryptedText: text };
  } catch {
    return { ...msg, decryptedText: "[Cannot decrypt]" };
  }
}
