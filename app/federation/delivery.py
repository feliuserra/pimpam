"""
Deliver ActivityPub activities to remote server inboxes.

Delivery is done inline (asyncio.gather) rather than via a background queue.
This is intentional for the initial version — keep it simple.
TODO: Move to a background task queue (ARQ + Redis) once follower counts grow.
"""
import asyncio
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.federation.crypto import sha256_digest, sign_request


async def deliver_activity(
    activity: dict,
    sender,  # User ORM instance (local, must have ap_private_key_pem)
    inbox_urls: list[str],
) -> None:
    """
    POST an AP activity to one or more remote inboxes, signed with the
    sender's RSA private key. Deduplicates shared inboxes by domain.
    """
    unique_inboxes = _deduplicate_inboxes(inbox_urls)
    body = json.dumps(activity).encode()
    key_id = f"https://{settings.domain}/users/{sender.username}#main-key"

    await asyncio.gather(
        *[_post(inbox, body, sender.ap_private_key_pem, key_id) for inbox in unique_inboxes],
        return_exceptions=True,  # don't let one failed delivery abort the others
    )


async def _post(inbox_url: str, body: bytes, private_key_pem: str, key_id: str) -> None:
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    digest = sha256_digest(body)
    signature = sign_request("POST", inbox_url, date, digest, private_key_pem, key_id)

    parsed = urlparse(inbox_url)
    headers = {
        "Host": parsed.netloc,
        "Date": date,
        "Digest": digest,
        "Signature": signature,
        "Content-Type": "application/activity+json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(inbox_url, content=body, headers=headers)
        except httpx.RequestError:
            pass  # Log and move on — remote servers can be unreliable


def _deduplicate_inboxes(inbox_urls: list[str]) -> list[str]:
    """Keep one inbox per domain — avoids duplicate delivery when using shared inboxes."""
    seen: set[str] = set()
    result = []
    for url in inbox_urls:
        domain = urlparse(url).netloc
        if domain not in seen:
            seen.add(domain)
            result.append(url)
    return result


