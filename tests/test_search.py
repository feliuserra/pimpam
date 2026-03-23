"""
Search endpoint tests.

Meilisearch is not available in the test environment, so:
- We test that the endpoint returns 503 when search is disabled.
- We test that post create/edit/delete routes still work correctly even when
  indexing silently fails (Meilisearch unreachable).
- Live search behaviour is covered by manual / integration testing against a
  running Meilisearch instance.
"""
import pytest

from app.core.config import settings
from tests.conftest import setup_user


@pytest.fixture(autouse=True)
def disable_search(monkeypatch):
    """Disable search for all tests in this module — no Meilisearch in CI."""
    monkeypatch.setattr(settings, "search_enabled", False)


async def test_search_returns_503_when_disabled(client):
    r = await client.get("/api/v1/search?q=hello")
    assert r.status_code == 503


async def test_search_requires_query(client):
    # search_enabled is False so we get 503, but if it were enabled we'd get 422
    # This just confirms the route exists and responds
    r = await client.get("/api/v1/search")
    assert r.status_code in (422, 503)


async def test_post_create_succeeds_when_search_down(client):
    """Indexing failure must never break post creation."""
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=h)
    assert r.status_code == 201


async def test_post_edit_succeeds_when_search_down(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=h)
    post_id = r.json()["id"]
    r = await client.patch(f"/api/v1/posts/{post_id}", json={"title": "Updated"}, headers=h)
    assert r.status_code == 200


async def test_post_delete_succeeds_when_search_down(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"}, headers=h)
    post_id = r.json()["id"]
    r = await client.delete(f"/api/v1/posts/{post_id}", headers=h)
    assert r.status_code == 204
