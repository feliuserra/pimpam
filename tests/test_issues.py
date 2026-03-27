"""Tests for the community issue tracker (/api/v1/issues/*)."""

from sqlalchemy import update

from app.models.user import User
from tests.conftest import get_test_db, setup_user


async def _make_admin(username: str):
    async for db in get_test_db():
        await db.execute(
            update(User).where(User.username == username).values(is_admin=True)
        )
        await db.commit()


async def _setup_admin(client, username="admin_user"):
    h = await setup_user(client, username)
    await _make_admin(username)
    return h


# ── Create ───────────────────────────────────────────────────────────


async def test_create_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Dark mode support",
            "description": "Please add a dark mode theme for better readability at night",
            "category": "feature",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Dark mode support"
    assert body["category"] == "feature"
    assert body["status"] == "open"
    assert body["vote_count"] == 0
    assert body["author_username"] == "alice"


async def test_create_issue_invalid_category(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Test issue",
            "description": "Some description here",
            "category": "invalid",
        },
    )
    assert r.status_code == 422


async def test_create_issue_requires_auth(client):
    r = await client.post(
        "/api/v1/issues",
        json={
            "title": "Test issue",
            "description": "Some description here",
            "category": "bug",
        },
    )
    assert r.status_code == 401


async def test_create_issue_title_too_short(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={"title": "Hi", "description": "Some description here", "category": "bug"},
    )
    assert r.status_code == 422


# ── List ─────────────────────────────────────────────────────────────


async def test_list_issues_empty(client):
    r = await client.get("/api/v1/issues")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_issues_sorted_by_votes(client):
    h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    # Create two issues
    await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Issue one here",
            "description": "First issue description",
            "category": "bug",
        },
    )
    r2 = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Issue two here",
            "description": "Second issue description",
            "category": "feature",
        },
    )
    id2 = r2.json()["id"]

    # Vote on issue 2
    await client.post(f"/api/v1/issues/{id2}/vote", headers=h)
    await client.post(f"/api/v1/issues/{id2}/vote", headers=bob_h)

    r = await client.get("/api/v1/issues?sort=votes")
    assert r.status_code == 200
    issues = r.json()
    assert len(issues) == 2
    assert issues[0]["id"] == id2  # most voted first


async def test_list_issues_filter_by_category(client):
    h = await setup_user(client, "alice")
    await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "A bug report",
            "description": "Something is broken here",
            "category": "bug",
        },
    )
    await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Feature request here",
            "description": "Add this new feature please",
            "category": "feature",
        },
    )

    r = await client.get("/api/v1/issues?category=bug")
    assert len(r.json()) == 1
    assert r.json()[0]["category"] == "bug"


async def test_list_issues_filter_by_status(client):
    admin_h = await _setup_admin(client)
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Some issue here",
            "description": "Issue description text",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    # Admin marks as in_progress
    await client.patch(
        f"/api/v1/issues/{issue_id}",
        headers=admin_h,
        json={"status": "in_progress"},
    )

    r = await client.get("/api/v1/issues?status=in_progress")
    assert len(r.json()) == 1
    r = await client.get("/api/v1/issues?status=open")
    assert len(r.json()) == 0


async def test_list_issues_shows_has_voted(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Voteable issue",
            "description": "This should be voteable",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]
    await client.post(f"/api/v1/issues/{issue_id}/vote", headers=h)

    r = await client.get("/api/v1/issues", headers=h)
    assert r.json()[0]["has_voted"] is True


# ── Get Single ───────────────────────────────────────────────────────


async def test_get_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Get this issue",
            "description": "Details about the issue",
            "category": "improvement",
        },
    )
    issue_id = r.json()["id"]
    r = await client.get(f"/api/v1/issues/{issue_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Get this issue"


async def test_get_issue_not_found(client):
    r = await client.get("/api/v1/issues/9999")
    assert r.status_code == 404


# ── Voting ───────────────────────────────────────────────────────────


async def test_vote_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Vote on this",
            "description": "Test voting mechanism here",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(f"/api/v1/issues/{issue_id}/vote", headers=h)
    assert r.status_code == 204

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    assert r.json()["vote_count"] == 1
    assert r.json()["has_voted"] is True


async def test_vote_idempotent(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Vote twice here",
            "description": "Should be idempotent vote",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    await client.post(f"/api/v1/issues/{issue_id}/vote", headers=h)
    await client.post(f"/api/v1/issues/{issue_id}/vote", headers=h)

    r = await client.get(f"/api/v1/issues/{issue_id}")
    assert r.json()["vote_count"] == 1


async def test_unvote_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Unvote test here",
            "description": "Testing the unvote feature",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    await client.post(f"/api/v1/issues/{issue_id}/vote", headers=h)
    r = await client.delete(f"/api/v1/issues/{issue_id}/vote", headers=h)
    assert r.status_code == 204

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    assert r.json()["vote_count"] == 0
    assert r.json()["has_voted"] is False


async def test_unvote_idempotent(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Unvote twice here",
            "description": "Should be idempotent unvote",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.delete(f"/api/v1/issues/{issue_id}/vote", headers=h)
    assert r.status_code == 204


async def test_vote_requires_auth(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Auth test issue",
            "description": "Testing auth for voting",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(f"/api/v1/issues/{issue_id}/vote")
    assert r.status_code == 401


async def test_vote_not_found(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues/9999/vote", headers=h)
    assert r.status_code == 404


# ── Comments ─────────────────────────────────────────────────────────


async def test_add_comment(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Commentable issue",
            "description": "Testing commenting feature",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/issues/{issue_id}/comments",
        headers=h,
        json={"content": "Great idea, I support this!"},
    )
    assert r.status_code == 201
    assert r.json()["content"] == "Great idea, I support this!"
    assert r.json()["author_username"] == "alice"

    # Check comment count updated
    r = await client.get(f"/api/v1/issues/{issue_id}")
    assert r.json()["comment_count"] == 1


async def test_list_comments(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Many comments issue",
            "description": "Issue with multiple comments",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    await client.post(
        f"/api/v1/issues/{issue_id}/comments", headers=h, json={"content": "First"}
    )
    await client.post(
        f"/api/v1/issues/{issue_id}/comments", headers=h, json={"content": "Second"}
    )

    r = await client.get(f"/api/v1/issues/{issue_id}/comments")
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["content"] == "First"


async def test_comment_requires_auth(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Auth comment test",
            "description": "Testing comment auth check",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(
        f"/api/v1/issues/{issue_id}/comments",
        json={"content": "Should fail"},
    )
    assert r.status_code == 401


async def test_comment_on_nonexistent_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues/9999/comments",
        headers=h,
        json={"content": "Should fail"},
    )
    assert r.status_code == 404


# ── Admin ────────────────────────────────────────────────────────────


async def test_admin_update_status(client):
    admin_h = await _setup_admin(client)
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Admin update test",
            "description": "Testing admin status update",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/issues/{issue_id}",
        headers=admin_h,
        json={"status": "in_progress"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


async def test_admin_mark_security(client):
    admin_h = await _setup_admin(client)
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Security concern here",
            "description": "This is a security related issue",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/issues/{issue_id}",
        headers=admin_h,
        json={"is_security": True},
    )
    assert r.status_code == 200
    assert r.json()["is_security"] is True


async def test_non_admin_cannot_update(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Normal user test",
            "description": "Non-admin should not update",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.patch(
        f"/api/v1/issues/{issue_id}",
        headers=h,
        json={"status": "completed"},
    )
    assert r.status_code == 403


async def test_admin_update_not_found(client):
    admin_h = await _setup_admin(client)
    r = await client.patch(
        "/api/v1/issues/9999",
        headers=admin_h,
        json={"status": "completed"},
    )
    assert r.status_code == 404


# ── Close / Reopen ──────────────────────────────────────────────────


async def test_author_can_close_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Close this issue",
            "description": "Author should be able to close",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]
    assert r.json()["is_closed"] is False

    r = await client.post(f"/api/v1/issues/{issue_id}/close", headers=h)
    assert r.status_code == 200
    assert r.json()["is_closed"] is True
    assert r.json()["closed_at"] is not None


async def test_author_can_reopen_issue(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Reopen this issue",
            "description": "Author should be able to reopen",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    await client.post(f"/api/v1/issues/{issue_id}/close", headers=h)
    r = await client.post(f"/api/v1/issues/{issue_id}/reopen", headers=h)
    assert r.status_code == 200
    assert r.json()["is_closed"] is False
    assert r.json()["closed_at"] is None


async def test_admin_can_close_any_issue(client):
    admin_h = await _setup_admin(client)
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Admin close test",
            "description": "Admin should close any issue",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(f"/api/v1/issues/{issue_id}/close", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["is_closed"] is True


async def test_non_author_cannot_close(client):
    h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Cannot close this",
            "description": "Non-author should not close",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(f"/api/v1/issues/{issue_id}/close", headers=bob_h)
    assert r.status_code == 403


async def test_close_already_closed(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Already closed issue",
            "description": "Should conflict on double close",
            "category": "feature",
        },
    )
    issue_id = r.json()["id"]

    await client.post(f"/api/v1/issues/{issue_id}/close", headers=h)
    r = await client.post(f"/api/v1/issues/{issue_id}/close", headers=h)
    assert r.status_code == 409


async def test_reopen_not_closed(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Not closed issue",
            "description": "Should conflict on reopen of open issue",
            "category": "bug",
        },
    )
    issue_id = r.json()["id"]

    r = await client.post(f"/api/v1/issues/{issue_id}/reopen", headers=h)
    assert r.status_code == 409


async def test_list_issues_filter_by_closed(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Open issue stays",
            "description": "This one stays open for filter",
            "category": "feature",
        },
    )
    r2 = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Closed issue here",
            "description": "This one will be closed for filter",
            "category": "bug",
        },
    )
    closed_id = r2.json()["id"]
    await client.post(f"/api/v1/issues/{closed_id}/close", headers=h)

    # Filter open only
    r = await client.get("/api/v1/issues?closed=false")
    assert all(not i["is_closed"] for i in r.json())
    assert len(r.json()) == 1

    # Filter closed only
    r = await client.get("/api/v1/issues?closed=true")
    assert all(i["is_closed"] for i in r.json())
    assert len(r.json()) == 1


# ── Polls ──────────────────────────────────────────────────────────


POLL_ISSUE = {
    "title": "Which feature next",
    "description": "Vote on what we should build next please",
    "category": "feature",
    "poll": {
        "question": "What should we build?",
        "options": [
            {"text": "Dark mode"},
            {"text": "Mobile app"},
            {"text": "Better search"},
        ],
    },
}


async def test_create_issue_with_poll(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    assert r.status_code == 201
    body = r.json()
    assert body["poll"] is not None
    poll = body["poll"]
    assert poll["question"] == "What should we build?"
    assert len(poll["options"]) == 3
    assert poll["options"][0]["text"] == "Dark mode"
    assert poll["options"][1]["text"] == "Mobile app"
    assert poll["options"][2]["text"] == "Better search"
    assert poll["total_votes"] == 0
    assert poll["user_voted_option_ids"] == []


async def test_create_issue_without_poll(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "No poll issue here",
            "description": "This issue has no poll attached",
            "category": "bug",
        },
    )
    assert r.status_code == 201
    assert r.json()["poll"] is None


async def test_poll_requires_at_least_two_options(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Bad poll issue here",
            "description": "Poll with only one option is invalid",
            "category": "feature",
            "poll": {
                "question": "Only one choice?",
                "options": [{"text": "Only option"}],
            },
        },
    )
    assert r.status_code == 422


async def test_poll_rejects_duplicate_options(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Duplicate poll options",
            "description": "Poll options must be unique text",
            "category": "feature",
            "poll": {
                "question": "Pick one?",
                "options": [{"text": "Same"}, {"text": "Same"}],
            },
        },
    )
    assert r.status_code == 422


async def test_vote_on_poll(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    option_id = r.json()["poll"]["options"][0]["id"]

    r = await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": option_id},
    )
    assert r.status_code == 204

    # Verify vote reflected
    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    poll = r.json()["poll"]
    assert poll["total_votes"] == 1
    assert option_id in poll["user_voted_option_ids"]
    assert poll["options"][0]["vote_count"] == 1


async def test_vote_poll_duplicate_returns_409(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    option_id = r.json()["poll"]["options"][0]["id"]

    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": option_id},
    )
    r = await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": option_id},
    )
    assert r.status_code == 409


async def test_single_choice_poll_replaces_vote(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    opt_a = r.json()["poll"]["options"][0]["id"]
    opt_b = r.json()["poll"]["options"][1]["id"]

    # Vote for option A
    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": opt_a},
    )
    # Vote for option B (should replace A in single-choice mode)
    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": opt_b},
    )

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    poll = r.json()["poll"]
    assert poll["total_votes"] == 1
    assert opt_b in poll["user_voted_option_ids"]
    assert opt_a not in poll["user_voted_option_ids"]
    # Option A should have 0, option B should have 1
    opts = {o["id"]: o["vote_count"] for o in poll["options"]}
    assert opts[opt_a] == 0
    assert opts[opt_b] == 1


async def test_unvote_poll(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    option_id = r.json()["poll"]["options"][0]["id"]

    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": option_id},
    )
    r = await client.request(
        "DELETE",
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": option_id},
    )
    assert r.status_code == 204

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    poll = r.json()["poll"]
    assert poll["total_votes"] == 0
    assert poll["user_voted_option_ids"] == []


async def test_poll_multiple_users_vote(client):
    alice_h = await setup_user(client, "alice")
    bob_h = await setup_user(client, "bob")

    r = await client.post("/api/v1/issues", headers=alice_h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    opt_a = r.json()["poll"]["options"][0]["id"]
    opt_b = r.json()["poll"]["options"][1]["id"]

    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=alice_h,
        json={"option_id": opt_a},
    )
    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=bob_h,
        json={"option_id": opt_b},
    )

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=alice_h)
    poll = r.json()["poll"]
    assert poll["total_votes"] == 2
    assert opt_a in poll["user_voted_option_ids"]

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=bob_h)
    poll = r.json()["poll"]
    assert opt_b in poll["user_voted_option_ids"]


async def test_poll_vote_requires_auth(client):
    h = await setup_user(client, "alice")
    r = await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)
    issue_id = r.json()["id"]
    option_id = r.json()["poll"]["options"][0]["id"]

    r = await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        json={"option_id": option_id},
    )
    assert r.status_code == 401


async def test_poll_shown_in_issue_list(client):
    h = await setup_user(client, "alice")
    await client.post("/api/v1/issues", headers=h, json=POLL_ISSUE)

    r = await client.get("/api/v1/issues")
    assert r.status_code == 200
    issues = r.json()
    assert len(issues) == 1
    assert issues[0]["poll"] is not None
    assert issues[0]["poll"]["question"] == "What should we build?"


async def test_allows_multiple_poll(client):
    h = await setup_user(client, "alice")
    r = await client.post(
        "/api/v1/issues",
        headers=h,
        json={
            "title": "Multi choice poll",
            "description": "Poll that allows multiple selections",
            "category": "feature",
            "poll": {
                "question": "Select all that apply",
                "options": [
                    {"text": "Option A"},
                    {"text": "Option B"},
                    {"text": "Option C"},
                ],
                "allows_multiple": True,
            },
        },
    )
    issue_id = r.json()["id"]
    opt_a = r.json()["poll"]["options"][0]["id"]
    opt_b = r.json()["poll"]["options"][1]["id"]

    # Vote for both options
    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": opt_a},
    )
    await client.post(
        f"/api/v1/issues/{issue_id}/poll/vote",
        headers=h,
        json={"option_id": opt_b},
    )

    r = await client.get(f"/api/v1/issues/{issue_id}", headers=h)
    poll = r.json()["poll"]
    assert poll["total_votes"] == 2
    assert opt_a in poll["user_voted_option_ids"]
    assert opt_b in poll["user_voted_option_ids"]
