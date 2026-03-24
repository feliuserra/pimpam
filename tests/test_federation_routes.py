"""
Integration tests for federation HTTP endpoints:
  - app/api/federation/wellknown.py  (webfinger, nodeinfo)
  - app/api/federation/actor_routes.py (actor, inbox, outbox, followers, following)
"""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import setup_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AP_ACCEPT = "application/activity+json"
HTML_ACCEPT = "text/html,application/xhtml+xml"


# ---------------------------------------------------------------------------
# /.well-known/webfinger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_webfinger_happy_path(client):
    """Valid acct:user@domain returns a JRD document."""
    await setup_user(client, "alice")
    from app.core.config import settings
    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": f"acct:alice@{settings.domain}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == f"acct:alice@{settings.domain}"
    assert any(link["rel"] == "self" for link in body["links"])


@pytest.mark.asyncio
async def test_webfinger_missing_acct_prefix(client):
    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": "alice@example.com"},
    )
    assert r.status_code == 400
    assert "acct:" in r.json()["detail"]


@pytest.mark.asyncio
async def test_webfinger_no_at_sign(client):
    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:alice"},
    )
    assert r.status_code == 400
    assert "Malformed" in r.json()["detail"]


@pytest.mark.asyncio
async def test_webfinger_wrong_domain(client):
    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": "acct:alice@otherdomain.example"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_webfinger_user_not_found(client):
    from app.core.config import settings
    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": f"acct:ghost@{settings.domain}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_webfinger_remote_user_rejected(client):
    """Remote (federated) users must not be resolvable via webfinger on this server."""
    from sqlalchemy import select
    from tests.conftest import get_test_db
    from app.models.user import User
    from app.core.config import settings

    # Create a local user first, then flip is_remote
    await setup_user(client, "remoteuser")
    async for session in get_test_db():
        result = await session.execute(select(User).where(User.username == "remoteuser"))
        u = result.scalar_one()
        u.is_remote = True
        await session.commit()

    r = await client.get(
        "/.well-known/webfinger",
        params={"resource": f"acct:remoteuser@{settings.domain}"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /.well-known/nodeinfo  and  /nodeinfo/2.1
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nodeinfo_discovery(client):
    r = await client.get("/.well-known/nodeinfo")
    assert r.status_code == 200
    body = r.json()
    assert "links" in body
    assert any("nodeinfo" in link["rel"] for link in body["links"])


@pytest.mark.asyncio
async def test_nodeinfo_document(client):
    await setup_user(client, "alice")
    r = await client.get("/nodeinfo/2.1")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "2.1"
    assert "activitypub" in body["protocols"]
    assert body["usage"]["users"]["total"] >= 1


# ---------------------------------------------------------------------------
# GET /users/{username} — Actor document
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_actor_ap_accept_returns_json(client):
    await setup_user(client, "alice")
    r = await client.get(
        "/users/alice",
        headers={"Accept": AP_ACCEPT},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "Person"
    assert "alice" in body["id"]


@pytest.mark.asyncio
async def test_get_actor_unknown_user_404(client):
    r = await client.get("/users/ghost", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_actor_html_accept_redirects(client):
    await setup_user(client, "alice")
    r = await client.get(
        "/users/alice",
        headers={"Accept": HTML_ACCEPT},
        follow_redirects=False,
    )
    # Either a redirect or the AP JSON (depending on Accept negotiation)
    assert r.status_code in (200, 302, 307, 308)


# ---------------------------------------------------------------------------
# GET /users/{username}/inbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_inbox_returns_ordered_collection(client):
    await setup_user(client, "alice")
    r = await client.get("/users/alice/inbox", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "OrderedCollection"
    assert body["totalItems"] == 0


@pytest.mark.asyncio
async def test_get_inbox_unknown_user_404(client):
    r = await client.get("/users/ghost/inbox", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /users/{username}/inbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_inbox_missing_signature_401(client):
    await setup_user(client, "alice")
    r = await client.post(
        "/users/alice/inbox",
        json={"type": "Follow"},
        headers={"Accept": AP_ACCEPT},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_post_inbox_with_mocked_signature(client):
    """With the signature dependency overridden, inbox should accept the activity."""
    from app.main import app
    from app.federation.signatures import verify_inbox_signature

    await setup_user(client, "alice")

    fake_actor = {"id": "https://remote.example/users/bob", "type": "Person"}

    async def _mock_sig():
        return fake_actor

    app.dependency_overrides[verify_inbox_signature] = _mock_sig
    try:
        with patch("app.federation.activity_handler.dispatch", new=AsyncMock()):
            r = await client.post(
                "/users/alice/inbox",
                json={"type": "Follow", "actor": "https://remote.example/users/bob"},
                headers={"Accept": AP_ACCEPT, "Content-Type": "application/json"},
            )
        assert r.status_code == 202
    finally:
        app.dependency_overrides.pop(verify_inbox_signature, None)


@pytest.mark.asyncio
async def test_post_inbox_unknown_user_404(client):
    """Even with mocked signature, posting to an unknown user's inbox is 404."""
    from app.main import app
    from app.federation.signatures import verify_inbox_signature

    async def _mock_sig():
        return {"id": "https://remote.example/users/bob"}

    app.dependency_overrides[verify_inbox_signature] = _mock_sig
    try:
        r = await client.post(
            "/users/ghost/inbox",
            json={"type": "Follow"},
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(verify_inbox_signature, None)


# ---------------------------------------------------------------------------
# GET /users/{username}/outbox
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_outbox_empty(client):
    await setup_user(client, "alice")
    r = await client.get("/users/alice/outbox", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "OrderedCollection"
    assert body["totalItems"] == 0
    assert body["orderedItems"] == []


@pytest.mark.asyncio
async def test_get_outbox_includes_posts(client):
    hdrs = await setup_user(client, "alice")
    await client.post("/api/v1/posts", headers=hdrs, json={"title": "Hello", "content": "World"})
    r = await client.get("/users/alice/outbox", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["totalItems"] >= 1
    assert any(item["type"] == "Create" for item in body["orderedItems"])


@pytest.mark.asyncio
async def test_get_outbox_unknown_user_404(client):
    r = await client.get("/users/ghost/outbox", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /users/{username}/followers  and  /following
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_followers_empty(client):
    await setup_user(client, "alice")
    r = await client.get("/users/alice/followers", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "OrderedCollection"
    assert body["totalItems"] == 0


@pytest.mark.asyncio
async def test_get_following_empty(client):
    await setup_user(client, "alice")
    r = await client.get("/users/alice/following", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "OrderedCollection"
    assert body["totalItems"] == 0


@pytest.mark.asyncio
async def test_get_followers_unknown_user_404(client):
    r = await client.get("/users/ghost/followers", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_following_unknown_user_404(client):
    r = await client.get("/users/ghost/following", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_followers_count_after_follow(client):
    """After alice follows bob, bob's followers count is 1."""
    alice_h = await setup_user(client, "alice")
    await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    r = await client.get("/users/bob/followers", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["totalItems"] == 1


@pytest.mark.asyncio
async def test_get_following_count_after_follow(client):
    """After alice follows bob, alice's following count is 1."""
    alice_h = await setup_user(client, "alice")
    await setup_user(client, "bob")
    await client.post("/api/v1/users/bob/follow", headers=alice_h)

    r = await client.get("/users/alice/following", headers={"Accept": AP_ACCEPT})
    assert r.status_code == 200
    body = r.json()
    assert body["totalItems"] == 1
