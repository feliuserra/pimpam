"""
FastAPI dependency for verifying HTTP Signatures on incoming inbox requests.
Extracts the keyId from the Signature header, fetches the remote actor's
public key (from cache), and verifies the signature.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.federation.crypto import verify_signature
from app.federation.fetcher import FederationFetchError, fetch_remote_actor


async def verify_inbox_signature(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Dependency that verifies the HTTP Signature of an incoming AP request.
    Returns the remote actor document on success.
    Raises 401 on any signature failure.
    """
    sig_header = request.headers.get("signature", "")
    if not sig_header:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Missing Signature header"
        )

    key_id = _extract_key_id(sig_header)
    if not key_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Malformed Signature header"
        )

    # The actor URL is the key ID without the fragment (#main-key)
    actor_ap_id = key_id.split("#")[0]

    try:
        actor_doc = await fetch_remote_actor(actor_ap_id, db)
    except FederationFetchError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Could not fetch signing actor"
        )

    public_key_pem = actor_doc.get("publicKey", {}).get("publicKeyPem", "")
    if not public_key_pem:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Actor has no public key"
        )

    # Verify the Digest header matches the actual request body
    body = await request.body()
    digest_header = request.headers.get("digest", "")
    if digest_header:
        from app.federation.crypto import sha256_digest

        expected_digest = sha256_digest(body)
        if digest_header != expected_digest:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Digest mismatch")
    elif body:
        # Body present but no Digest header — require it for POST requests
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Missing Digest header"
        )

    headers = dict(request.headers)
    path = request.url.path
    method = request.method

    if not verify_signature(headers, method, path, public_key_pem):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    return actor_doc


def _extract_key_id(sig_header: str) -> str | None:
    for part in sig_header.split(","):
        k, _, v = part.strip().partition("=")
        if k.strip() == "keyId":
            return v.strip().strip('"')
    return None
