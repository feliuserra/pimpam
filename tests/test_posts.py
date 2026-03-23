from tests.conftest import setup_user


async def _create_community_and_post(client, username="alice"):
    h = await setup_user(client, username)
    await client.post("/api/v1/communities", headers=h, json={"name": "general"})
    community_r = await client.get("/api/v1/communities/general")
    cid = community_r.json()["id"]
    post_r = await client.post("/api/v1/posts", headers=h, json={
        "title": "Hello world", "content": "First post", "community_id": cid
    })
    return h, post_r.json()


async def test_create_post(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", headers=h, json={
        "title": "Hello", "content": "World"
    })
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Hello"
    assert body["karma"] == 1        # author auto-vote
    assert body["is_edited"] is False
    assert body["is_removed"] is False


async def test_create_post_requires_content_or_url(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/posts", headers=h, json={"title": "No body"})
    assert r.status_code == 422


async def test_create_post_unauthenticated(client):
    r = await client.post("/api/v1/posts", json={"title": "Hello", "content": "World"})
    assert r.status_code == 401


async def test_get_post(client):
    h, post = await _create_community_and_post(client)
    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == post["id"]


async def test_get_post_not_found(client):
    r = await client.get("/api/v1/posts/9999")
    assert r.status_code == 404


async def test_edit_post(client):
    h, post = await _create_community_and_post(client)
    r = await client.patch(f"/api/v1/posts/{post['id']}", headers=h, json={
        "title": "Updated title"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Updated title"
    assert body["is_edited"] is True
    assert body["edited_at"] is not None


async def test_edit_post_not_owner(client):
    h, post = await _create_community_and_post(client, username="alice")
    bob_h = await setup_user(client, "bob")
    r = await client.patch(f"/api/v1/posts/{post['id']}", headers=bob_h, json={
        "title": "Hijacked"
    })
    assert r.status_code == 403


async def test_delete_post(client):
    h, post = await _create_community_and_post(client)
    r = await client.delete(f"/api/v1/posts/{post['id']}", headers=h)
    assert r.status_code == 204

    r = await client.get(f"/api/v1/posts/{post['id']}")
    assert r.status_code == 404


async def test_delete_post_not_owner(client):
    h, post = await _create_community_and_post(client, username="alice")
    bob_h = await setup_user(client, "bob")
    r = await client.delete(f"/api/v1/posts/{post['id']}", headers=bob_h)
    assert r.status_code == 403


async def test_list_community_posts(client):
    h, post = await _create_community_and_post(client)
    r = await client.get("/api/v1/communities/general/posts")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["id"] == post["id"]


async def test_list_community_posts_no_auth_required(client):
    await _create_community_and_post(client)
    # Unauthenticated access should still work
    r = await client.get("/api/v1/communities/general/posts")
    assert r.status_code == 200
