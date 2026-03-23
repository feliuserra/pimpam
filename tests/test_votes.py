from tests.conftest import setup_user


async def _setup(client):
    """alice creates a post; bob is ready to vote on it."""
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    post_r = await client.post("/api/v1/posts", headers=alice_h, json={
        "title": "Votable post", "content": "Vote on me"
    })
    post = post_r.json()
    return alice_h, bob_h, post


async def test_upvote(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})
    assert r.status_code == 200
    assert r.json()["direction"] == 1


async def test_downvote(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": -1})
    assert r.status_code == 200
    assert r.json()["direction"] == -1


async def test_vote_updates_post_karma(client):
    alice_h, bob_h, post = await _setup(client)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})
    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.json()["karma"] == 2  # started at 1 (author auto-vote) + 1


async def test_downvote_updates_post_karma(client):
    alice_h, bob_h, post = await _setup(client)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": -1})
    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.json()["karma"] == 0  # 1 - 1


async def test_vote_updates_author_karma(client):
    alice_h, bob_h, post = await _setup(client)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})
    r = await client.get("/api/v1/users/me", headers=alice_h)
    assert r.json()["karma"] == 1


async def test_change_vote(client):
    alice_h, bob_h, post = await _setup(client)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})
    # Change to downvote
    r = await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": -1})
    assert r.status_code == 200
    assert r.json()["direction"] == -1

    karma_r = await client.get(f"/api/v1/posts/{post['id']}")
    assert karma_r.json()["karma"] == 0  # 1 (author) - 1 (net of changed vote)


async def test_cannot_vote_own_post(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.post(f"/api/v1/posts/{post['id']}/vote", headers=alice_h, json={"direction": 1})
    assert r.status_code == 403


async def test_invalid_vote_direction(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 0})
    assert r.status_code == 422


async def test_retract_vote(client):
    alice_h, bob_h, post = await _setup(client)
    await client.post(f"/api/v1/posts/{post['id']}/vote", headers=bob_h, json={"direction": 1})
    r = await client.delete(f"/api/v1/posts/{post['id']}/vote", headers=bob_h)
    assert r.status_code == 204

    karma_r = await client.get(f"/api/v1/posts/{post['id']}")
    assert karma_r.json()["karma"] == 1  # back to author's auto-vote


async def test_retract_nonexistent_vote(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.delete(f"/api/v1/posts/{post['id']}/vote", headers=bob_h)
    assert r.status_code == 404


async def test_cannot_retract_own_author_vote(client):
    alice_h, bob_h, post = await _setup(client)
    r = await client.delete(f"/api/v1/posts/{post['id']}/vote", headers=alice_h)
    assert r.status_code == 403
