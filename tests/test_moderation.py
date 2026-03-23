from tests.conftest import setup_user, register


async def _setup(client):
    """
    alice creates a community (making her a mod).
    bob joins the community and creates a post.
    Returns (alice_h, bob_h, community, post).
    """
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    await client.post("/api/v1/communities", headers=alice_h, json={
        "name": "general", "description": "Test community"
    })
    community_r = await client.get("/api/v1/communities/general")
    community = community_r.json()

    # Bob joins and creates a post in the community
    await client.post("/api/v1/communities/general/join", headers=bob_h)
    post_r = await client.post("/api/v1/posts", headers=bob_h, json={
        "title": "Bob's post", "content": "Hello", "community_id": community["id"]
    })
    return alice_h, bob_h, community, post_r.json()


# --- Post removal ---

async def test_mod_remove_post(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.delete(
        f"/api/v1/communities/general/posts/{post['id']}", headers=alice_h
    )
    assert r.status_code == 204


async def test_removed_post_hidden_from_public(client):
    alice_h, bob_h, community, post = await _setup(client)
    await client.delete(f"/api/v1/communities/general/posts/{post['id']}", headers=alice_h)

    # Public listing should not show removed post
    r = await client.get("/api/v1/communities/general/posts")
    assert r.status_code == 200
    assert all(p["id"] != post["id"] for p in r.json())


async def test_removed_post_visible_to_mod(client):
    alice_h, bob_h, community, post = await _setup(client)
    await client.delete(f"/api/v1/communities/general/posts/{post['id']}", headers=alice_h)

    # Mod listing should include removed post
    r = await client.get("/api/v1/communities/general/posts", headers=alice_h)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert post["id"] in ids
    removed = next(p for p in r.json() if p["id"] == post["id"])
    assert removed["is_removed"] is True


async def test_mod_restore_post(client):
    alice_h, bob_h, community, post = await _setup(client)
    await client.delete(f"/api/v1/communities/general/posts/{post['id']}", headers=alice_h)
    r = await client.post(
        f"/api/v1/communities/general/posts/{post['id']}/restore", headers=alice_h
    )
    assert r.status_code == 204

    # Post is visible again
    public_r = await client.get("/api/v1/communities/general/posts")
    ids = [p["id"] for p in public_r.json()]
    assert post["id"] in ids


async def test_non_mod_cannot_remove_post(client):
    alice_h, bob_h, community, post = await _setup(client)
    # Bob is not a mod
    r = await client.delete(
        f"/api/v1/communities/general/posts/{post['id']}", headers=bob_h
    )
    assert r.status_code == 403


# --- Bans ---

async def test_propose_ban(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.post("/api/v1/communities/general/bans", headers=alice_h, json={
        "target_username": "bob",
        "reason": "Repeated spam",
        "coc_violation": "spam",
        "is_permanent": False,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["vote_count"] == 1     # proposer's vote is automatic
    assert body["required_votes"] == 10


async def test_ban_proposal_duplicate_vote(client):
    alice_h, bob_h, community, post = await _setup(client)
    proposal_r = await client.post("/api/v1/communities/general/bans", headers=alice_h, json={
        "target_username": "bob",
        "reason": "Spam",
        "coc_violation": "spam",
        "is_permanent": True,
    })
    proposal_id = proposal_r.json()["id"]
    r = await client.post(
        f"/api/v1/communities/general/bans/{proposal_id}/vote", headers=alice_h
    )
    assert r.status_code == 409


async def test_list_bans_empty(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.get("/api/v1/communities/general/bans", headers=alice_h)
    assert r.status_code == 200
    assert r.json() == []


async def test_non_mod_cannot_propose_ban(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.post("/api/v1/communities/general/bans", headers=bob_h, json={
        "target_username": "alice",
        "reason": "Test",
        "coc_violation": "spam",
        "is_permanent": False,
    })
    assert r.status_code == 403


async def test_cannot_ban_self(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.post("/api/v1/communities/general/bans", headers=alice_h, json={
        "target_username": "alice",
        "reason": "Test",
        "coc_violation": "spam",
        "is_permanent": False,
    })
    assert r.status_code == 400


# --- Mod promotion ---

async def test_propose_mod_promotion(client):
    alice_h, bob_h, community, post = await _setup(client)
    r = await client.post("/api/v1/communities/general/moderators", headers=alice_h, json={
        "target_username": "bob"
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["vote_count"] == 1     # proposer's vote is automatic
    assert body["required_votes"] == 2  # max(2, ceil(1 mod / 2))


async def test_propose_mod_promotion_duplicate_vote(client):
    alice_h, bob_h, community, post = await _setup(client)
    proposal_r = await client.post(
        "/api/v1/communities/general/moderators", headers=alice_h, json={"target_username": "bob"}
    )
    proposal_id = proposal_r.json()["id"]
    r = await client.post(
        f"/api/v1/communities/general/moderators/{proposal_id}/vote", headers=alice_h
    )
    assert r.status_code == 409


async def test_cannot_propose_non_member(client):
    alice_h, bob_h, community, post = await _setup(client)
    # carol is not a member
    await register(client, "carol")
    r = await client.post("/api/v1/communities/general/moderators", headers=alice_h, json={
        "target_username": "carol"
    })
    assert r.status_code == 400


async def test_non_mod_cannot_propose_promotion(client):
    alice_h, bob_h, community, post = await _setup(client)
    carol_h = await setup_user(client, "carol")
    await client.post("/api/v1/communities/general/join", headers=carol_h)
    r = await client.post("/api/v1/communities/general/moderators", headers=carol_h, json={
        "target_username": "bob"
    })
    assert r.status_code == 403
