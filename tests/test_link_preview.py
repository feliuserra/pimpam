from unittest.mock import AsyncMock, patch

import httpx

from tests.conftest import setup_user

PREVIEW_URL = "/api/v1/posts/link-preview"


def _mock_client(*, status_code=200, content_type="text/html; charset=utf-8", body=""):
    """Return a patched httpx.AsyncClient that returns a fake response."""
    resp = httpx.Response(
        status_code=status_code,
        headers={"content-type": content_type},
        content=body.encode("utf-8") if isinstance(body, str) else body,
        request=httpx.Request("GET", "https://example.com"),
    )
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=resp)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    return patch("app.api.v1.posts.httpx.AsyncClient", return_value=mock_http)


def _mock_client_error(exc):
    """Return a patched httpx.AsyncClient whose get() raises an exception."""
    mock_http = AsyncMock()
    mock_http.get = AsyncMock(side_effect=exc)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    return patch("app.api.v1.posts.httpx.AsyncClient", return_value=mock_http)


OG_HTML = """\
<!doctype html>
<html>
<head>
    <meta property="og:title" content="Example Title" />
    <meta property="og:description" content="A short description." />
    <meta property="og:image" content="https://example.com/img.png" />
    <meta property="og:site_name" content="Example" />
    <title>Fallback Title</title>
</head>
<body><p>Hello</p></body>
</html>
"""

TITLE_ONLY_HTML = """\
<!doctype html>
<html>
<head><title>Just a Title</title></head>
<body></body>
</html>
"""

NO_METADATA_HTML = """\
<!doctype html>
<html>
<head></head>
<body><p>No metadata here.</p></body>
</html>
"""


# ---------- Happy path ----------


async def test_link_preview_full_og(client):
    h = await setup_user(client, "alice")
    with _mock_client(body=OG_HTML):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com"}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Example Title"
    assert data["description"] == "A short description."
    assert data["image"] == "https://example.com/img.png"
    assert data["site_name"] == "Example"


async def test_link_preview_falls_back_to_title(client):
    h = await setup_user(client, "alice")
    with _mock_client(body=TITLE_ONLY_HTML):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com/page"}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Just a Title"
    assert data["description"] is None
    assert data["image"] is None


async def test_link_preview_no_metadata(client):
    h = await setup_user(client, "alice")
    with _mock_client(body=NO_METADATA_HTML):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com/bare"}
        )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] is None
    assert data["description"] is None


# ---------- Error handling ----------


async def test_link_preview_fetch_error_returns_empty(client):
    h = await setup_user(client, "alice")
    with _mock_client_error(httpx.ConnectError("Connection refused")):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://down.example.com"}
        )
    assert r.status_code == 200
    assert r.json()["title"] is None


async def test_link_preview_timeout_returns_empty(client):
    h = await setup_user(client, "alice")
    with _mock_client_error(httpx.ReadTimeout("timed out")):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://slow.example.com"}
        )
    assert r.status_code == 200
    assert r.json()["title"] is None


async def test_link_preview_non_html_returns_empty(client):
    h = await setup_user(client, "alice")
    with _mock_client(content_type="application/json", body='{"key":"val"}'):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://api.example.com"}
        )
    assert r.status_code == 200
    assert r.json()["title"] is None


async def test_link_preview_image_content_type_returns_empty(client):
    h = await setup_user(client, "alice")
    with _mock_client(content_type="image/png", body=""):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com/photo.png"}
        )
    assert r.status_code == 200
    assert r.json()["title"] is None


# ---------- Auth ----------


async def test_link_preview_requires_auth(client):
    r = await client.get(PREVIEW_URL, params={"url": "https://example.com"})
    assert r.status_code in (401, 403)


async def test_link_preview_missing_url_param(client):
    h = await setup_user(client, "alice")
    r = await client.get(PREVIEW_URL, headers=h)
    assert r.status_code == 422


# ---------- Edge cases ----------


async def test_link_preview_og_title_takes_precedence(client):
    h = await setup_user(client, "alice")
    html = '<html><head><meta property="og:title" content="OG Wins" /><title>Loses</title></head></html>'
    with _mock_client(body=html):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com"}
        )
    assert r.json()["title"] == "OG Wins"


async def test_link_preview_large_body_truncated(client):
    h = await setup_user(client, "alice")
    html = (
        '<html><head><meta property="og:title" content="Big Page" /></head><body>'
        + "x" * (2 * 1024 * 1024)
        + "</body></html>"
    )
    with _mock_client(body=html):
        r = await client.get(
            PREVIEW_URL, headers=h, params={"url": "https://example.com/big"}
        )
    assert r.status_code == 200
    assert r.json()["title"] == "Big Page"
