from tests.conftest import register, setup_user


async def test_create_community(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/communities", headers=h, json={
        "name": "general", "description": "General chat"
    })
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "general"
    assert body["member_count"] == 1  # creator is auto-joined


async def test_create_community_duplicate(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "general"})
    r = await client.post("/api/v1/communities", headers=h, json={"name": "general"})
    assert r.status_code == 409


async def test_create_community_unauthenticated(client):
    r = await client.post("/api/v1/communities", json={"name": "general"})
    assert r.status_code == 401


async def test_get_community(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "general"})
    r = await client.get("/api/v1/communities/general")
    assert r.status_code == 200
    assert r.json()["name"] == "general"


async def test_get_community_not_found(client):
    r = await client.get("/api/v1/communities/doesnotexist")
    assert r.status_code == 404


async def test_list_communities_default(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "aaa"})
    await client.post("/api/v1/communities", headers=h, json={"name": "bbb"})
    r = await client.get("/api/v1/communities")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_list_communities_alphabetical(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/communities", headers=h, json={"name": "zebra"})
    await client.post("/api/v1/communities", headers=h, json={"name": "apple"})
    r = await client.get("/api/v1/communities?sort=alphabetical")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert names == sorted(names)


async def test_join_community(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/communities", headers=alice_h, json={"name": "general"})

    r = await client.post("/api/v1/communities/general/join", headers=bob_h)
    assert r.status_code == 204

    community = await client.get("/api/v1/communities/general")
    assert community.json()["member_count"] == 2


async def test_leave_community(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    await client.post("/api/v1/communities", headers=alice_h, json={"name": "general"})
    await client.post("/api/v1/communities/general/join", headers=bob_h)

    r = await client.post("/api/v1/communities/general/leave", headers=bob_h)
    assert r.status_code == 204

    community = await client.get("/api/v1/communities/general")
    assert community.json()["member_count"] == 1
