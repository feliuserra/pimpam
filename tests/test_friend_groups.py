"""
Integration tests for the friend groups feature.

Covers group CRUD, member management, and post visibility enforcement.
"""
import pytest
import pytest_asyncio

from tests.conftest import setup_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def follow(client, headers_from, username_to):
    """Follow username_to as the user identified by headers_from. Returns the followed user's id."""
    await client.post(f"/api/v1/users/{username_to}/follow", headers=headers_from)
    r = await client.get(f"/api/v1/users/{username_to}", headers=headers_from)
    return r.json()["id"]


async def create_group(client, hdrs, name):
    r = await client.post("/api/v1/friend-groups", json={"name": name}, headers=hdrs)
    assert r.status_code == 201, r.text
    return r.json()


async def add_member(client, hdrs, group_id, user_id):
    r = await client.post(
        f"/api/v1/friend-groups/{group_id}/members",
        json={"user_id": user_id},
        headers=hdrs,
    )
    return r


# ---------------------------------------------------------------------------
# Group CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_group(client):
    hdrs = await setup_user(client, "alice")
    group = await create_group(client, hdrs, "My Crew")
    assert group["name"] == "My Crew"
    assert group["is_close_friends"] is False
    assert group["member_count"] == 0


@pytest.mark.asyncio
async def test_list_groups_close_friends_first(client):
    hdrs = await setup_user(client, "alice")
    # Create Close Friends first, then a named group
    await client.get("/api/v1/friend-groups/close-friends", headers=hdrs)
    await create_group(client, hdrs, "Weekend people")

    r = await client.get("/api/v1/friend-groups", headers=hdrs)
    assert r.status_code == 200
    groups = r.json()
    assert groups[0]["is_close_friends"] is True


@pytest.mark.asyncio
async def test_close_friends_auto_created(client):
    hdrs = await setup_user(client, "alice")
    r1 = await client.get("/api/v1/friend-groups/close-friends", headers=hdrs)
    assert r1.status_code == 200
    assert r1.json()["is_close_friends"] is True

    # Calling again returns the same group (idempotent)
    r2 = await client.get("/api/v1/friend-groups/close-friends", headers=hdrs)
    assert r2.json()["id"] == r1.json()["id"]


@pytest.mark.asyncio
async def test_rename_group(client):
    hdrs = await setup_user(client, "alice")
    group = await create_group(client, hdrs, "Old name")
    r = await client.patch(
        f"/api/v1/friend-groups/{group['id']}",
        json={"name": "New name"},
        headers=hdrs,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New name"


@pytest.mark.asyncio
async def test_cannot_rename_close_friends(client):
    hdrs = await setup_user(client, "alice")
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs)).json()
    r = await client.patch(
        f"/api/v1/friend-groups/{cf['id']}",
        json={"name": "Renamed"},
        headers=hdrs,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_group(client):
    hdrs = await setup_user(client, "alice")
    group = await create_group(client, hdrs, "Temp group")
    r = await client.delete(f"/api/v1/friend-groups/{group['id']}", headers=hdrs)
    assert r.status_code == 204

    r2 = await client.get(f"/api/v1/friend-groups/{group['id']}", headers=hdrs)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_close_friends(client):
    hdrs = await setup_user(client, "alice")
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs)).json()
    r = await client.delete(f"/api/v1/friend-groups/{cf['id']}", headers=hdrs)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_member_must_follow(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")

    group = await create_group(client, hdrs_alice, "Crew")
    # Get bob's id without following
    r_bob = await client.get("/api/v1/users/bob", headers=hdrs_alice)
    bob_id = r_bob.json()["id"]

    r = await add_member(client, hdrs_alice, group["id"], bob_id)
    assert r.status_code == 400
    assert "follow" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_member_success(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")

    group = await create_group(client, hdrs_alice, "Crew")
    bob_id = await follow(client, hdrs_alice, "bob")

    r = await add_member(client, hdrs_alice, group["id"], bob_id)
    assert r.status_code == 201
    members = r.json()["members"]
    assert any(m["user_id"] == bob_id for m in members)


@pytest.mark.asyncio
async def test_add_member_already_member(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")

    group = await create_group(client, hdrs_alice, "Crew")
    bob_id = await follow(client, hdrs_alice, "bob")
    await add_member(client, hdrs_alice, group["id"], bob_id)

    r = await add_member(client, hdrs_alice, group["id"], bob_id)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_cannot_add_yourself(client):
    hdrs_alice = await setup_user(client, "alice")
    r_me = await client.get("/api/v1/users/me", headers=hdrs_alice)
    alice_id = r_me.json()["id"]

    group = await create_group(client, hdrs_alice, "Crew")
    r = await add_member(client, hdrs_alice, group["id"], alice_id)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_remove_member(client):
    hdrs_alice = await setup_user(client, "alice")
    await setup_user(client, "bob")

    group = await create_group(client, hdrs_alice, "Crew")
    bob_id = await follow(client, hdrs_alice, "bob")
    await add_member(client, hdrs_alice, group["id"], bob_id)

    r = await client.delete(
        f"/api/v1/friend-groups/{group['id']}/members/{bob_id}",
        headers=hdrs_alice,
    )
    assert r.status_code == 204

    detail = (await client.get(f"/api/v1/friend-groups/{group['id']}", headers=hdrs_alice)).json()
    assert not any(m["user_id"] == bob_id for m in detail["members"])


# ---------------------------------------------------------------------------
# Post visibility
# ---------------------------------------------------------------------------

async def _create_group_post(client, hdrs, group_id):
    r = await client.post("/api/v1/posts", json={
        "title": "Private post",
        "content": "Only for the group",
        "visibility": "group",
        "friend_group_id": group_id,
    }, headers=hdrs)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_group_post_visible_to_owner(client):
    hdrs_alice = await setup_user(client, "alice")
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    post = await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=hdrs_alice)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_group_post_visible_to_member(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    bob_id = await follow(client, hdrs_alice, "bob")
    await add_member(client, hdrs_alice, cf["id"], bob_id)

    post = await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=hdrs_bob)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_group_post_hidden_from_non_member(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_charlie = await setup_user(client, "charlie")

    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    post = await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get(f"/api/v1/posts/{post['id']}", headers=hdrs_charlie)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_group_post_hidden_from_anonymous(client):
    hdrs_alice = await setup_user(client, "alice")
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    post = await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_group_post_not_in_public_feed(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    # Bob follows Alice but is NOT in her Close Friends group
    await follow(client, hdrs_bob, "alice")

    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get("/api/v1/feed", headers=hdrs_bob)
    assert r.status_code == 200
    assert all(p["visibility"] == "public" for p in r.json())


@pytest.mark.asyncio
async def test_group_post_in_member_feed(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    # Bob follows Alice AND is in her Close Friends
    await follow(client, hdrs_bob, "alice")  # Bob follows Alice
    bob_id = await follow(client, hdrs_alice, "bob")  # Alice follows Bob (needed to add him); returns Bob's id
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    await add_member(client, hdrs_alice, cf["id"], bob_id)

    await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.get("/api/v1/feed", headers=hdrs_bob)
    assert r.status_code == 200
    assert any(p["visibility"] == "group" for p in r.json())


@pytest.mark.asyncio
async def test_cannot_share_group_post(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    bob_id = await follow(client, hdrs_alice, "bob")
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    await add_member(client, hdrs_alice, cf["id"], bob_id)

    post = await _create_group_post(client, hdrs_alice, cf["id"])

    r = await client.post(f"/api/v1/posts/{post['id']}/share", json={}, headers=hdrs_bob)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_community_post_must_be_public(client):
    hdrs_alice = await setup_user(client, "alice")
    # Create a community
    r = await client.post("/api/v1/communities", json={"name": "testcomm", "description": "x"}, headers=hdrs_alice)
    comm_id = r.json()["id"]

    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()
    r = await client.post("/api/v1/posts", json={
        "title": "Bad post",
        "content": "Should fail",
        "community_id": comm_id,
        "visibility": "group",
        "friend_group_id": cf["id"],
    }, headers=hdrs_alice)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_group_post_requires_group_id(client):
    hdrs_alice = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", json={
        "title": "Bad post",
        "content": "Missing friend_group_id",
        "visibility": "group",
    }, headers=hdrs_alice)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cannot_post_to_others_group(client):
    hdrs_alice = await setup_user(client, "alice")
    hdrs_bob = await setup_user(client, "bob")

    # Bob tries to post to Alice's group
    cf = (await client.get("/api/v1/friend-groups/close-friends", headers=hdrs_alice)).json()

    r = await client.post("/api/v1/posts", json={
        "title": "Sneaky post",
        "content": "Should fail",
        "visibility": "group",
        "friend_group_id": cf["id"],
    }, headers=hdrs_bob)
    assert r.status_code == 403
