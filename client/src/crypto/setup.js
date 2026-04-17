/**
 * E2EE key setup — ensures the current device has a keypair.
 *
 * Called after login. If no private key exists in IndexedDB,
 * generates a fresh keypair and publishes the public key to the server.
 */

import { loadPrivateKey, generateKeyPair, storePrivateKey, exportPublicKey } from "./keys";
import { updateMe } from "../api/users";

/**
 * Ensure E2EE keys exist for this device.
 * Returns true if a new keypair was generated (new device notice should be shown).
 */
export async function ensureKeysExist() {
  try {
    const existing = await loadPrivateKey();
    if (existing) return false;

    // New device or first login — generate keypair
    const keyPair = await generateKeyPair();
    await storePrivateKey(keyPair.privateKey);

    // Publish public key to server
    const publicKeyBase64 = await exportPublicKey(keyPair.publicKey);
    await updateMe({ e2ee_public_key: publicKeyBase64 });

    return true; // new keypair was generated
  } catch (err) {
    console.error("E2EE key setup failed:", err);
    throw err;
  }
}
