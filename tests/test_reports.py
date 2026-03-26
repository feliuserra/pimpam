"""Tests for content reporting: post and comment reports."""

from tests.conftest import setup_user


async def test_report_post(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Bob creates a post
    post_r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Offensive", "content": "Bad content"},
    )
    post_id = post_r.json()["id"]

    r = await client.post(
        f"/api/v1/posts/{post_id}/report",
        headers=alice_h,
        json={"reason": "Harassment"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["content_type"] == "post"
    assert data["content_id"] == post_id


async def test_report_post_not_found(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/posts/99999/report",
        headers=alice_h,
        json={"reason": "Spam"},
    )
    assert r.status_code == 404


async def test_cannot_report_own_post(client):
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "My post", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    r = await client.post(
        f"/api/v1/posts/{post_id}/report",
        headers=alice_h,
        json={"reason": "Testing"},
    )
    assert r.status_code == 400


async def test_duplicate_post_report(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    post_r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Bad", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    await client.post(
        f"/api/v1/posts/{post_id}/report",
        headers=alice_h,
        json={"reason": "Spam"},
    )
    r = await client.post(
        f"/api/v1/posts/{post_id}/report",
        headers=alice_h,
        json={"reason": "Spam again"},
    )
    assert r.status_code == 409


async def test_report_comment(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Bob creates a post and a comment
    post_r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Post", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    comment_r = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=bob_h,
        json={"content": "Offensive comment"},
    )
    comment_id = comment_r.json()["id"]

    r = await client.post(
        f"/api/v1/comments/{comment_id}/report",
        headers=alice_h,
        json={"reason": "Hate speech"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["content_type"] == "comment"
    assert data["content_id"] == comment_id


async def test_report_comment_not_found(client):
    alice_h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/comments/99999/report",
        headers=alice_h,
        json={"reason": "Spam"},
    )
    assert r.status_code == 404


async def test_cannot_report_own_comment(client):
    alice_h = await setup_user(client, "alice")

    post_r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Post", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    comment_r = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=alice_h,
        json={"content": "My comment"},
    )
    comment_id = comment_r.json()["id"]

    r = await client.post(
        f"/api/v1/comments/{comment_id}/report",
        headers=alice_h,
        json={"reason": "Testing"},
    )
    assert r.status_code == 400


async def test_duplicate_comment_report(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    post_r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Post", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    comment_r = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        headers=bob_h,
        json={"content": "Bad comment"},
    )
    comment_id = comment_r.json()["id"]

    await client.post(
        f"/api/v1/comments/{comment_id}/report",
        headers=alice_h,
        json={"reason": "Spam"},
    )
    r = await client.post(
        f"/api/v1/comments/{comment_id}/report",
        headers=alice_h,
        json={"reason": "Spam again"},
    )
    assert r.status_code == 409


async def test_report_requires_reason(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    post_r = await client.post(
        "/api/v1/posts",
        headers=bob_h,
        json={"title": "Bad", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    # Empty reason
    r = await client.post(
        f"/api/v1/posts/{post_id}/report",
        headers=alice_h,
        json={"reason": ""},
    )
    assert r.status_code == 422


async def test_report_requires_auth(client):
    alice_h = await setup_user(client, "alice")
    post_r = await client.post(
        "/api/v1/posts",
        headers=alice_h,
        json={"title": "Post", "content": "Content"},
    )
    post_id = post_r.json()["id"]

    r = await client.post(
        f"/api/v1/posts/{post_id}/report",
        json={"reason": "Spam"},
    )
    assert r.status_code == 401
