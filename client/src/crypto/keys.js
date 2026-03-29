/**
 * E2EE key management — RSA-OAEP 2048-bit keypair, multi-device.
 *
 * Private key is stored in IndexedDB (never leaves the device).
 * Public key is exported as base64-encoded SPKI for server storage.
 * Device ID is stored alongside the key for multi-device fan-out.
 */

const DB_NAME = "pimpam-e2ee";
const STORE_NAME = "keys";
const PRIVATE_KEY_ID = "privateKey";
const DEVICE_ID_KEY = "deviceId";
const VERIFIED_CONTACTS_STORE = "verified_contacts";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 2);
    req.onupgradeneeded = (event) => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
      if (!db.objectStoreNames.contains(VERIFIED_CONTACTS_STORE)) {
        db.createObjectStore(VERIFIED_CONTACTS_STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Store the private CryptoKey in IndexedDB. */
export async function storePrivateKey(privateKey) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(privateKey, PRIVATE_KEY_ID);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Load the private CryptoKey from IndexedDB. Returns null if missing. */
export async function loadPrivateKey() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(PRIVATE_KEY_ID);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/** Store the device ID in IndexedDB. */
export async function storeDeviceId(deviceId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(deviceId, DEVICE_ID_KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Load the device ID from IndexedDB. Returns null if missing. */
export async function loadDeviceId() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(DEVICE_ID_KEY);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/** Generate a new RSA-OAEP 2048-bit keypair (non-extractable private key). */
export async function generateKeyPair() {
  return crypto.subtle.generateKey(
    {
      name: "RSA-OAEP",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    false,
    ["encrypt", "decrypt"],
  );
}

/** Generate an extractable RSA-OAEP 2048-bit keypair (for backup export). */
export async function generateExtractableKeyPair() {
  return crypto.subtle.generateKey(
    {
      name: "RSA-OAEP",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true, // extractable — allows PKCS8 export for backup
    ["encrypt", "decrypt"],
  );
}

/** Re-import an extractable private key as non-extractable for storage. */
export async function reimportAsNonExtractable(extractablePrivateKey) {
  const pkcs8 = await crypto.subtle.exportKey("pkcs8", extractablePrivateKey);
  return crypto.subtle.importKey(
    "pkcs8",
    pkcs8,
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["decrypt"],
  );
}

/** Export an extractable private key to PKCS8 ArrayBuffer (for backup wrapping). */
export async function exportPrivateKeyPkcs8(extractablePrivateKey) {
  return crypto.subtle.exportKey("pkcs8", extractablePrivateKey);
}

/** Export a public CryptoKey to base64 string (SPKI format). */
export async function exportPublicKey(publicKey) {
  const spki = await crypto.subtle.exportKey("spki", publicKey);
  return btoa(String.fromCharCode(...new Uint8Array(spki)));
}

/** Import a base64-encoded SPKI public key into a CryptoKey. */
export async function importPublicKey(base64) {
  const binary = atob(base64);
  const buffer = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    buffer[i] = binary.charCodeAt(i);
  }
  return crypto.subtle.importKey(
    "spki",
    buffer.buffer,
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["encrypt"],
  );
}
