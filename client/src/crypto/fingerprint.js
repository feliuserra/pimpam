/**
 * Safety number computation for key verification.
 *
 * A safety number is derived from both users' public key fingerprints.
 * Displayed as a 60-digit numeric code (12 groups of 5 digits),
 * identical regardless of which side views it (sorted inputs).
 */

/**
 * Compute SHA-256 fingerprint of a base64-encoded SPKI public key.
 * @param {string} publicKeyBase64
 * @returns {Promise<string>} — 64-char hex string
 */
export async function computeFingerprint(publicKeyBase64) {
  const binary = atob(publicKeyBase64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Compute a safety number from two fingerprints.
 * The result is deterministic regardless of argument order.
 * @param {string} myFingerprint — 64-char hex
 * @param {string} theirFingerprint — 64-char hex
 * @returns {Promise<string>} — 60-digit numeric code (12 groups of 5, space-separated)
 */
export async function computeSafetyNumber(myFingerprint, theirFingerprint) {
  // Sort to ensure same output regardless of who views
  const sorted = [myFingerprint, theirFingerprint].sort();
  const combined = sorted.join("");

  // Hash the combined fingerprints
  const encoded = new TextEncoder().encode(combined);
  const hash = await crypto.subtle.digest("SHA-256", encoded);
  const bytes = new Uint8Array(hash);

  // Convert 32 bytes into 60 decimal digits (12 groups of 5)
  // Each group: take 2+ bytes, mod 100000
  const digits = [];
  for (let i = 0; i < 12; i++) {
    // Use 2.5 bytes per group (30 bytes total, we have 32)
    const offset = Math.floor((i * 5) / 2);
    const val =
      (bytes[offset] << 16) |
      (bytes[offset + 1] << 8) |
      (bytes[(offset + 2) % 32] || 0);
    digits.push(String(val % 100000).padStart(5, "0"));
  }

  return digits.join(" ");
}
