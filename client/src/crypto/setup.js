/**
 * E2EE key setup — ensures the current device has a keypair and is registered.
 *
 * Called after login. If no private key / device ID exists in IndexedDB,
 * generates a fresh keypair and registers a new device on the server.
 * If a backup exists from another device, signals recovery is needed.
 */

import {
  loadPrivateKey,
  loadDeviceId,
  generateExtractableKeyPair,
  reimportAsNonExtractable,
  storePrivateKey,
  storeDeviceId,
  exportPublicKey,
} from "./keys";
import { registerDevice, getMyDevices, getAvailableBackups } from "../api/devices";

/**
 * Parse User-Agent into a friendly device name like "Chrome on macOS".
 */
function detectDeviceName() {
  const ua = navigator.userAgent;

  let browser = "Browser";
  if (ua.includes("Firefox/")) browser = "Firefox";
  else if (ua.includes("Edg/")) browser = "Edge";
  else if (ua.includes("Chrome/") && !ua.includes("Edg/")) browser = "Chrome";
  else if (ua.includes("Safari/") && !ua.includes("Chrome/")) browser = "Safari";

  let os = "Unknown";
  if (ua.includes("Mac OS X")) os = "macOS";
  else if (ua.includes("Windows")) os = "Windows";
  else if (ua.includes("Android")) os = "Android";
  else if (ua.includes("iPhone") || ua.includes("iPad")) os = "iOS";
  else if (ua.includes("Linux")) os = "Linux";

  return `${browser} on ${os}`;
}

/**
 * Ensure E2EE keys exist for this device.
 *
 * Returns:
 * - { isNewDevice: false, deviceId } — existing device found and active
 * - { isNewDevice: true, deviceId, extractablePrivateKey } — new keypair generated, device registered
 * - { needsRecovery: true, backupDeviceId } — backup available, caller should show recovery prompt
 */
export async function ensureKeysExist() {
  try {
    const [existing, storedDeviceId] = await Promise.all([
      loadPrivateKey(),
      loadDeviceId(),
    ]);

    // Check if we already have a key + device
    if (existing && storedDeviceId) {
      // Verify the device is still active on the server
      try {
        const { data: devices } = await getMyDevices();
        const stillActive = devices.some((d) => d.id === storedDeviceId);
        if (stillActive) {
          return { isNewDevice: false, deviceId: storedDeviceId };
        }
      } catch {
        // Server unreachable — assume device is still valid
        return { isNewDevice: false, deviceId: storedDeviceId };
      }
      // Device was revoked or removed — fall through to new device flow
    }

    // Check if user has any existing backups (for recovery on new device)
    try {
      const { data: backups } = await getAvailableBackups();
      if (backups.length > 0) {
        return {
          needsRecovery: true,
          backupDeviceId: backups[0].device_id,
        };
      }
    } catch {
      // No backups or server error — proceed with new key generation
    }

    // New device — generate extractable keypair
    const keyPair = await generateExtractableKeyPair();

    // Store non-extractable copy in IndexedDB
    const nonExtractable = await reimportAsNonExtractable(keyPair.privateKey);
    await storePrivateKey(nonExtractable);

    // Register device on server
    const publicKeyBase64 = await exportPublicKey(keyPair.publicKey);
    const { data: device } = await registerDevice({
      device_name: detectDeviceName(),
      public_key: publicKeyBase64,
    });

    await storeDeviceId(device.id);

    return {
      isNewDevice: true,
      deviceId: device.id,
      extractablePrivateKey: keyPair.privateKey,
    };
  } catch (err) {
    console.error("E2EE key setup failed:", err);
    throw err;
  }
}
