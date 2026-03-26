import pytest

from tests.conftest import setup_user

pytestmark = pytest.mark.asyncio


async def _create_community(client, auth, name="testcommunity"):
    r = await client.post(
        "/api/v1/communities",
        json={"name": name, "description": "test"},
        headers=auth,
    )
    assert r.status_code == 201
    return r.json()


async def _create_post_in_community(client, auth, community_name):
    r = await client.post(
        "/api/v1/posts",
        json={
            "title": "Test post",
            "content": "content",
            "community_id": (
                await client.get(f"/api/v1/communities/{community_name}", headers=auth)
            ).json()["id"],
        },
        headers=auth,
    )
    assert r.status_code == 201
    return r.json()


async def test_moderator_creates_pick(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "testpicks")
    post = await _create_post_in_community(client, auth, "testpicks")

    r = await client.post(
        "/api/v1/communities/testpicks/picks",
        json={"post_id": post["id"], "note": "Great post!"},
        headers=auth,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["curator_username"] == "alice"
    assert data["note"] == "Great post!"


async def test_non_moderator_cannot_pick(client):
    owner_auth = await setup_user(client, "owner")
    member_auth = await setup_user(client, "member")

    await _create_community(client, owner_auth, "restricted")
    await client.post("/api/v1/communities/restricted/join", headers=member_auth)
    post = await _create_post_in_community(client, owner_auth, "restricted")

    r = await client.post(
        "/api/v1/communities/restricted/picks",
        json={"post_id": post["id"]},
        headers=member_auth,
    )
    assert r.status_code == 403


async def test_post_must_belong_to_community(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "comm1")
    await _create_community(client, auth, "comm2")

    # Post in comm2
    post = await _create_post_in_community(client, auth, "comm2")

    # Try to pick it in comm1
    r = await client.post(
        "/api/v1/communities/comm1/picks",
        json={"post_id": post["id"]},
        headers=auth,
    )
    assert r.status_code == 400


async def test_max_3_picks_enforced(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "limited")

    posts = []
    for i in range(4):
        posts.append(await _create_post_in_community(client, auth, "limited"))

    # First 3 should succeed
    for i in range(3):
        r = await client.post(
            "/api/v1/communities/limited/picks",
            json={"post_id": posts[i]["id"]},
            headers=auth,
        )
        assert r.status_code == 201

    # Fourth should fail
    r = await client.post(
        "/api/v1/communities/limited/picks",
        json={"post_id": posts[3]["id"]},
        headers=auth,
    )
    assert r.status_code == 409


async def test_remove_pick(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "cleanup")
    post = await _create_post_in_community(client, auth, "cleanup")

    r = await client.post(
        "/api/v1/communities/cleanup/picks",
        json={"post_id": post["id"]},
        headers=auth,
    )
    pick_id = r.json()["id"]

    r = await client.delete(
        f"/api/v1/communities/cleanup/picks/{pick_id}",
        headers=auth,
    )
    assert r.status_code == 204


async def test_list_picks(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "showcase")
    post = await _create_post_in_community(client, auth, "showcase")

    await client.post(
        "/api/v1/communities/showcase/picks",
        json={"post_id": post["id"], "note": "Editor's choice"},
        headers=auth,
    )

    r = await client.get("/api/v1/communities/showcase/picks", headers=auth)
    assert r.status_code == 200
    picks = r.json()
    assert len(picks) == 1
    assert picks[0]["curator_username"] == "alice"
    assert picks[0]["note"] == "Editor's choice"
    assert picks[0]["post"] is not None
    assert picks[0]["post"]["id"] == post["id"]


async def test_duplicate_pick_rejected(client):
    auth = await setup_user(client, "alice")
    await _create_community(client, auth, "dupes")
    post = await _create_post_in_community(client, auth, "dupes")

    r1 = await client.post(
        "/api/v1/communities/dupes/picks",
        json={"post_id": post["id"]},
        headers=auth,
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/communities/dupes/picks",
        json={"post_id": post["id"]},
        headers=auth,
    )
    assert r2.status_code == 409
