"""
For You discover feed.

Formula (publishable, spreadsheet-reproducible):
    SELECT posts WHERE
      (post has a hashtag the user subscribes to)
      OR (post is picked in a community the user joined)
    EXCLUDE removed posts, blocked users, private visibility
    ORDER BY created_at DESC
    DEDUPLICATE BY post_id (merge reasons)

No scoring. No weighting. Strictly chronological.
"""

from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.community import CommunityMember
from app.models.curated_pick import CuratedPick
from app.models.hashtag import Hashtag, PostHashtag
from app.models.hashtag_subscription import HashtagSubscription
from app.models.post import Post
from app.models.user import User


async def get_for_you_feed(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    before_id: int | None = None,
) -> list[dict]:
    """Return posts for the user's personalized discover feed with attribution."""

    # 1. Get user's subscribed hashtag IDs
    sub_hashtag_ids = (
        select(HashtagSubscription.hashtag_id)
        .where(HashtagSubscription.user_id == user_id)
        .scalar_subquery()
    )

    # 2. Get user's joined community IDs
    joined_community_ids = (
        select(CommunityMember.community_id)
        .where(CommunityMember.user_id == user_id)
        .scalar_subquery()
    )

    # 3. Get blocked user IDs (both directions)
    blocked_ids_q = select(Block.blocked_id).where(Block.blocker_id == user_id)
    blocker_ids_q = select(Block.blocker_id).where(Block.blocked_id == user_id)

    # 4. Hashtag-matched posts: post IDs with their matching hashtag names
    hashtag_posts = (
        select(
            PostHashtag.post_id.label("post_id"),
            Hashtag.name.label("hashtag_name"),
        )
        .join(Hashtag, PostHashtag.hashtag_id == Hashtag.id)
        .where(PostHashtag.hashtag_id.in_(sub_hashtag_ids))
    )

    # 5. Get all matching post IDs (union)
    hashtag_post_ids = select(PostHashtag.post_id).where(
        PostHashtag.hashtag_id.in_(sub_hashtag_ids)
    )
    picked_post_ids = select(CuratedPick.post_id).where(
        CuratedPick.community_id.in_(joined_community_ids)
    )
    all_post_ids = union_all(hashtag_post_ids, picked_post_ids).subquery()

    # 7. Fetch the actual posts
    query = (
        select(Post)
        .where(
            Post.id.in_(select(all_post_ids.c.post_id)),
            Post.is_removed == False,  # noqa: E712
            Post.visibility == "public",
            Post.author_id.notin_(blocked_ids_q),
            Post.author_id.notin_(blocker_ids_q),
        )
        .order_by(Post.created_at.desc())
        .limit(limit)
    )

    if before_id is not None:
        subq = select(Post.created_at).where(Post.id == before_id).scalar_subquery()
        query = query.where(Post.created_at < subq)

    result = await db.execute(query)
    posts = list(result.scalars().all())

    if not posts:
        return []

    # 8. Build attribution for each post
    post_ids = [p.id for p in posts]

    # Hashtag attributions
    ht_result = await db.execute(hashtag_posts.where(PostHashtag.post_id.in_(post_ids)))
    hashtag_attrs: dict[int, list[str]] = {}
    for row in ht_result:
        hashtag_attrs.setdefault(row.post_id, []).append(row.hashtag_name)

    # Pick attributions
    pick_result = await db.execute(
        select(CuratedPick, User.username)
        .join(User, CuratedPick.curator_id == User.id)
        .where(
            CuratedPick.post_id.in_(post_ids),
            CuratedPick.community_id.in_(joined_community_ids),
        )
    )

    # Also need community names for picks
    from app.models.community import Community

    pick_attrs: dict[int, list[dict]] = {}
    for pick, curator_username in pick_result:
        pick_attrs.setdefault(pick.post_id, []).append(
            {
                "curator_username": curator_username,
                "curator_id": pick.curator_id,
                "community_id": pick.community_id,
                "note": pick.note,
            }
        )

    # Fetch community names for picks
    community_ids_needed = set()
    for attrs in pick_attrs.values():
        for a in attrs:
            community_ids_needed.add(a["community_id"])

    community_names: dict[int, str] = {}
    if community_ids_needed:
        cn_result = await db.execute(
            select(Community.id, Community.name).where(
                Community.id.in_(community_ids_needed)
            )
        )
        community_names = {r.id: r.name for r in cn_result}

    # 9. Assemble results
    results = []
    for post in posts:
        attribution = []
        for tag_name in hashtag_attrs.get(post.id, []):
            attribution.append(
                {
                    "type": "hashtag",
                    "hashtag": tag_name,
                }
            )
        for pick_info in pick_attrs.get(post.id, []):
            attribution.append(
                {
                    "type": "pick",
                    "curator_username": pick_info["curator_username"],
                    "community_name": community_names.get(
                        pick_info["community_id"], ""
                    ),
                    "note": pick_info["note"],
                }
            )
        results.append({"post": post, "attribution": attribution})

    return results
