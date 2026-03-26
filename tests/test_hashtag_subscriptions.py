import pytest

from tests.conftest import setup_user

pytestmark = pytest.mark.asyncio


async def _create_hashtag_post(client, auth, title="#photography test post"):
    """Create a post with a hashtag so the hashtag exists."""
    r = await client.post(
        "/api/v1/posts",
        json={"title": title, "content": "test"},
        headers=auth,
    )
    assert r.status_code == 201
    return r.json()


async def test_subscribe_to_hashtag(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth)

    r = await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    assert r.status_code == 201


async def test_subscribe_already_subscribed(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth)

    await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    r = await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    assert r.status_code == 409


async def test_unsubscribe(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth)

    await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    r = await client.delete("/api/v1/hashtags/photography/subscribe", headers=auth)
    assert r.status_code == 204


async def test_unsubscribe_not_subscribed(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth)

    r = await client.delete("/api/v1/hashtags/photography/subscribe", headers=auth)
    assert r.status_code == 404


async def test_list_subscriptions(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth, "#photography one")
    await _create_hashtag_post(client, auth, "#music another")

    await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    await client.post("/api/v1/hashtags/music/subscribe", headers=auth)

    r = await client.get("/api/v1/hashtags/subscriptions", headers=auth)
    assert r.status_code == 200
    names = {s["hashtag_name"] for s in r.json()}
    assert names == {"photography", "music"}


async def test_hashtag_detail_shows_subscription_status(client):
    auth = await setup_user(client, "alice")
    await _create_hashtag_post(client, auth)

    # Before subscribing
    r = await client.get("/api/v1/hashtags/photography", headers=auth)
    assert r.status_code == 200
    assert r.json()["is_subscribed"] is False

    # After subscribing
    await client.post("/api/v1/hashtags/photography/subscribe", headers=auth)
    r = await client.get("/api/v1/hashtags/photography", headers=auth)
    assert r.json()["is_subscribed"] is True
    assert r.json()["subscriber_count"] == 1


async def test_subscribe_nonexistent_hashtag(client):
    auth = await setup_user(client, "alice")
    r = await client.post("/api/v1/hashtags/doesnotexist/subscribe", headers=auth)
    assert r.status_code == 404
