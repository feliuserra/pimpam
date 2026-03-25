/**
 * E2EE key management — RSA-OAEP 2048-bit keypair.
 *
 * Private key is stored in IndexedDB (never leaves the device).
 * Public key is exported as base64-encoded SPKI for server storage.
 */

const DB_NAME = "pimpam-e2ee";
const STORE_NAME = "keys";
const PRIVATE_KEY_ID = "privateKey";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME);
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

/** Generate a new RSA-OAEP 2048-bit keypair. */
export async function generateKeyPair() {
  return crypto.subtle.generateKey(
    {
      name: "RSA-OAEP",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    false, // private key is NOT extractable
    ["encrypt", "decrypt"],
  );
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
