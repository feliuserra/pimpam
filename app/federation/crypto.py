"""
RSA key generation, HTTP Signature creation, and HTTP Signature verification.

Implements draft-cavage-http-signatures-12, which is the version Mastodon,
Pixelfed, and Lemmy all use. Do not upgrade to the IETF RFC 9421 spec until
the Fediverse has broadly adopted it.
"""
import base64
import hashlib
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def generate_rsa_keypair() -> tuple[str, str]:
    """Generate a 2048-bit RSA key pair. Returns (private_pem, public_pem)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def sha256_digest(body: bytes) -> str:
    """Return the SHA-256 Digest header value for a request body."""
    return "SHA-256=" + base64.b64encode(hashlib.sha256(body).digest()).decode()


def sign_request(
    method: str,
    url: str,
    date: str,
    digest: str,
    private_key_pem: str,
    key_id: str,
) -> str:
    """
    Build the value of the HTTP Signature header for an outgoing request.
    The caller is responsible for setting Date and Digest headers first.
    """
    parsed = urlparse(url)
    signed_string = "\n".join([
        f"(request-target): {method.lower()} {parsed.path}",
        f"host: {parsed.netloc}",
        f"date: {date}",
        f"digest: {digest}",
    ])
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    raw_sig = private_key.sign(signed_string.encode(), padding.PKCS1v15(), hashes.SHA256())
    signature = base64.b64encode(raw_sig).decode()
    return (
        f'keyId="{key_id}",'
        f'algorithm="rsa-sha256",'
        f'headers="(request-target) host date digest",'
        f'signature="{signature}"'
    )


def verify_signature(
    headers: dict[str, str],
    method: str,
    path: str,
    public_key_pem: str,
) -> bool:
    """
    Verify an incoming HTTP Signature against the sender's public key.
    Returns True if valid, False for any failure (wrong key, bad format, etc.).
    """
    try:
        sig_header = headers.get("signature", "")
        # Parse key=value pairs, handling quoted values
        params: dict[str, str] = {}
        for part in sig_header.split(","):
            k, _, v = part.strip().partition("=")
            params[k.strip()] = v.strip().strip('"')

        raw_sig = base64.b64decode(params["signature"])
        header_names = params["headers"].split()

        signed_parts = []
        for h in header_names:
            if h == "(request-target)":
                signed_parts.append(f"(request-target): {method.lower()} {path}")
            else:
                signed_parts.append(f"{h}: {headers[h.lower()]}")
        signed_string = "\n".join(signed_parts)

        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        public_key.verify(raw_sig, signed_string.encode(), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False
