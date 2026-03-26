"""Shared OpenGraph metadata fetcher with Redis caching and SSRF protection."""

import hashlib
import ipaddress
import logging
import socket
from html.parser import HTMLParser

import httpx

from app.core.cache import cache_get, cache_set
from app.core.config import settings

logger = logging.getLogger("pimpam.og_parser")

MAX_BODY_BYTES = 1_048_576  # 1 MB
LINK_PREVIEW_UA = "PimPam/1.0 LinkPreview (+https://pimpam.org)"
_CACHE_PREFIX = "link_preview:"


class OGParser(HTMLParser):
    """Minimal HTML parser that extracts OpenGraph meta tags and the <title>."""

    def __init__(self) -> None:
        super().__init__()
        self.og: dict[str, str] = {}
        self.title: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []
        self._head_done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._head_done:
            return
        if tag == "title":
            self._in_title = True
            self._title_parts = []
            return
        if tag == "meta":
            attr_map = {k.lower(): v for k, v in attrs if v is not None}
            prop = attr_map.get("property", "")
            if prop.startswith("og:") and "content" in attr_map:
                key = prop[3:]
                self.og.setdefault(key, attr_map["content"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_parts).strip() or None
        if tag == "head":
            self._head_done = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def _is_private_ip(hostname: str) -> bool:
    """Reject requests to private/loopback IP ranges to prevent SSRF."""
    try:
        for info in socket.getaddrinfo(hostname, None):
            addr = ipaddress.ip_address(info[4][0])
            if addr.is_private or addr.is_loopback or addr.is_reserved:
                return True
    except (socket.gaierror, ValueError):
        return True
    return False


async def fetch_og_metadata(
    url: str,
    *,
    timeout: float | None = None,
) -> dict:
    """Fetch OpenGraph metadata from a URL.

    Returns dict with keys: title, description, image, site_name.
    All values are optional strings. Returns empty dict on any failure.
    Uses Redis cache to avoid redundant fetches.
    """
    if timeout is None:
        timeout = settings.story_link_preview_timeout

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    cached = await cache_get(f"{_CACHE_PREFIX}{url_hash}")
    if cached is not None:
        return cached

    try:
        parsed = httpx.URL(url)
        if _is_private_ip(str(parsed.host)):
            logger.warning("SSRF blocked: %s resolves to private IP", parsed.host)
            return {}
    except Exception:
        return {}

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            max_redirects=3,
            follow_redirects=True,
            headers={"User-Agent": LINK_PREVIEW_UA},
        ) as http:
            response = await http.get(url)
    except (httpx.HTTPError, ValueError):
        return {}

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        return {}

    body = response.content[:MAX_BODY_BYTES]
    try:
        html_text = body.decode("utf-8", errors="replace")
    except Exception:
        return {}

    parser = OGParser()
    try:
        parser.feed(html_text)
    except Exception:
        return {}

    result = {
        "title": parser.og.get("title") or parser.title,
        "description": parser.og.get("description"),
        "image": parser.og.get("image"),
        "site_name": parser.og.get("site_name"),
    }

    await cache_set(f"{_CACHE_PREFIX}{url_hash}", result, ttl=3600)

    return result
