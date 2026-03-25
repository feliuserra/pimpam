"""Tests for GET /api/v1/communities/joined endpoint."""

from tests.conftest import setup_user


async def test_joined_communities_empty(client):
    """A new user with no joined communities gets an empty list."""
    h = await setup_user(client, "alice")
    r = await client.get("/api/v1/communities/joined", headers=h)
    assert r.status_code == 200
    assert r.json() == []


async def test_joined_communities_includes_created(client):
    """Creating a community auto-joins the creator."""
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "general"})

    r = await client.get("/api/v1/communities/joined", headers=h)
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "general" in names


async def test_joined_communities_includes_joined(client):
    """Joining a community makes it appear in the joined list."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "music"})

    # Bob joins the community
    await client.post("/api/v1/communities/music/join", headers=bob_h)

    r = await client.get("/api/v1/communities/joined", headers=bob_h)
    names = [c["name"] for c in r.json()]
    assert "music" in names


async def test_joined_communities_excludes_unjoined(client):
    """Communities the user hasn't joined don't appear."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "secret"})

    r = await client.get("/api/v1/communities/joined", headers=bob_h)
    assert r.json() == []


async def test_joined_communities_after_leave(client):
    """Leaving a community removes it from the joined list."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={"name": "temp"})
    await client.post("/api/v1/communities/temp/join", headers=bob_h)

    # Verify it's in the list
    r = await client.get("/api/v1/communities/joined", headers=bob_h)
    assert len(r.json()) == 1

    # Leave and verify it's gone
    await client.post("/api/v1/communities/temp/leave", headers=bob_h)
    r = await client.get("/api/v1/communities/joined", headers=bob_h)
    assert r.json() == []


async def test_joined_communities_alphabetical_order(client):
    """Communities are returned in alphabetical order."""
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "zebra"})
    await client.post("/api/v1/communities", headers=h, json={"name": "apple"})
    await client.post("/api/v1/communities", headers=h, json={"name": "mango"})

    r = await client.get("/api/v1/communities/joined", headers=h)
    names = [c["name"] for c in r.json()]
    assert names == sorted(names)


async def test_joined_communities_unauthenticated(client):
    """Requires authentication."""
    r = await client.get("/api/v1/communities/joined")
    assert r.status_code == 401
