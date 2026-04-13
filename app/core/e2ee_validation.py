"""
Validation for E2EE public keys (RSA-OAEP, SPKI format).

The server never holds private keys, but it validates that uploaded
public keys are well-formed SPKI-encoded RSA keys before storing them.
"""

import base64
import hashlib

# ASN.1 OID for RSA encryption (1.2.840.113549.1.1.1) inside SPKI.
# The SPKI header for an RSA key begins with a SEQUENCE containing
# this AlgorithmIdentifier. We check for the OID bytes anywhere
# in the first 24 bytes of the decoded SPKI.
_RSA_OID = bytes.fromhex("06092a864886f70d010101")

# RSA-2048 SPKI is ~294 bytes.  Allow a generous range for future key sizes.
_MIN_SPKI_BYTES = 200
_MAX_SPKI_BYTES = 800


def validate_spki_public_key(base64_key: str) -> str:
    """Validate a base64-encoded SPKI RSA public key.

    Returns the SHA-256 hex fingerprint of the decoded bytes on success.
    Raises ``ValueError`` with a human-readable message on failure.
    """
    # --- Decode ---
    try:
        raw = base64.b64decode(base64_key, validate=True)
    except Exception:
        raise ValueError("Public key is not valid base64")

    # --- Size ---
    if len(raw) < _MIN_SPKI_BYTES:
        raise ValueError(
            f"Public key too short ({len(raw)} bytes, minimum {_MIN_SPKI_BYTES})"
        )
    if len(raw) > _MAX_SPKI_BYTES:
        raise ValueError(
            f"Public key too long ({len(raw)} bytes, maximum {_MAX_SPKI_BYTES})"
        )

    # --- RSA OID ---
    # The OID appears early in the SPKI header.
    if _RSA_OID not in raw[:24]:
        raise ValueError("Public key does not contain the RSA algorithm identifier")

    # --- Fingerprint ---
    return hashlib.sha256(raw).hexdigest()
