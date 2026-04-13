/**
 * Client-side contact verification storage.
 *
 * Stores verified contact fingerprints in IndexedDB.
 * When a contact's key changes, the verification is automatically invalid
 * because the stored fingerprint won't match the new key.
 */

const DB_NAME = "pimpam-e2ee";
const STORE_NAME = "verified_contacts";

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 2);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("keys")) {
        db.createObjectStore("keys");
      }
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Save a verified contact's fingerprint.
 * @param {number} contactUserId
 * @param {string} fingerprint — 64-char hex SHA-256 of their public key
 */
export async function saveVerification(contactUserId, fingerprint) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(
      { fingerprint, verifiedAt: new Date().toISOString() },
      String(contactUserId),
    );
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Get a verified contact's stored fingerprint.
 * @param {number} contactUserId
 * @returns {Promise<{fingerprint: string, verifiedAt: string} | null>}
 */
export async function getVerification(contactUserId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).get(String(contactUserId));
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Remove a contact's verification (e.g. when their key changes).
 * @param {number} contactUserId
 */
export async function clearVerification(contactUserId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(String(contactUserId));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
