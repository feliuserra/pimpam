"""
Serialize local users and posts as ActivityPub JSON-LD documents.
Returns plain dicts — not Pydantic models — because AP's @context array
cannot be cleanly expressed in Pydantic without significant boilerplate.
"""
from app.core.config import settings
from app.federation.constants import AP_CONTEXT, PUBLIC_STREAM


def actor_id(username: str) -> str:
    return f"https://{settings.domain}/users/{username}"


def build_actor(user) -> dict:
    """Build an AP Person actor document for a local user."""
    base = actor_id(user.username)
    doc = {
        "@context": AP_CONTEXT,
        "type": "Person",
        "id": base,
        "url": f"https://{settings.domain}/@{user.username}",
        "preferredUsername": user.username,
        "name": user.display_name or user.username,
        "summary": user.bio or "",
        "inbox": f"{base}/inbox",
        "outbox": f"{base}/outbox",
        "followers": f"{base}/followers",
        "following": f"{base}/following",
        "publicKey": {
            "id": f"{base}#main-key",
            "owner": base,
            "publicKeyPem": user.ap_public_key_pem,
        },
        "endpoints": {
            "sharedInbox": f"https://{settings.domain}/inbox",
        },
    }
    if user.avatar_url:
        doc["icon"] = {"type": "Image", "mediaType": "image/jpeg", "url": user.avatar_url}
    return doc


def build_note(post, author) -> dict:
    """Build an AP Note object for a local post."""
    note_url = f"https://{settings.domain}/posts/{post.id}"
    # AP Note has no title field; synthesize from content or use the title directly.
    content = post.content or post.title
    return {
        "@context": AP_CONTEXT,
        "type": "Note",
        "id": note_url,
        "url": note_url,
        "attributedTo": actor_id(author.username),
        "content": content,
        "published": post.created_at.isoformat(),
        "to": [PUBLIC_STREAM],
        "cc": [f"{actor_id(author.username)}/followers"],
    }


def build_create(post, author) -> dict:
    """Wrap a Note in a Create activity for delivery or outbox."""
    note = build_note(post, author)
    return {
        "@context": AP_CONTEXT,
        "type": "Create",
        "id": f"{note['id']}/activity",
        "actor": actor_id(author.username),
        "published": note["published"],
        "to": note["to"],
        "cc": note["cc"],
        "object": note,
    }


def build_follow(follower_username: str, followed_ap_id: str) -> dict:
    """Build a Follow activity from a local user to a remote actor."""
    follower = actor_id(follower_username)
    return {
        "@context": AP_CONTEXT,
        "type": "Follow",
        "id": f"{follower}#follow-{followed_ap_id.split('/')[-1]}",
        "actor": follower,
        "object": followed_ap_id,
    }


def build_accept(local_username: str, follow_activity: dict) -> dict:
    """Build an Accept activity in response to an incoming Follow."""
    base = actor_id(local_username)
    return {
        "@context": AP_CONTEXT,
        "type": "Accept",
        "id": f"{base}#accept-{follow_activity.get('id', 'follow').split('/')[-1]}",
        "actor": base,
        "object": follow_activity,
    }


def ordered_collection(collection_id: str, items: list, total: int) -> dict:
    """Build an AP OrderedCollection document."""
    return {
        "@context": AP_CONTEXT,
        "type": "OrderedCollection",
        "id": collection_id,
        "totalItems": total,
        "orderedItems": items,
    }
