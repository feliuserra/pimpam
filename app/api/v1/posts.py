import logging
from html.parser import HTMLParser

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import settings
from app.core.dependencies import CurrentUser, DBSession, OptionalUser
from app.core.limiter import limiter
from app.core.redis import publish_to_user
from app.core.search import deindex_post, index_post
from app.crud.friend_group import get_group, is_member
from app.crud.post import (
    annotate_post_with_user_vote,
    create_post,
    create_share,
    delete_post,
    edit_post,
    get_post,
)
from app.crud.user import (
    get_local_follower_ids,
    get_remote_follower_inboxes,
    get_user_by_id,
)
from app.crud.vote import cast_vote, retract_vote
from app.federation.actor import (
    build_announce,
    build_create,
    build_like,
    build_undo_like,
)
from app.federation.delivery import deliver_activity
from app.schemas.comment import ShareCreate
from app.schemas.post import LinkPreview, PostCreate, PostPublic, PostUpdate
from app.schemas.vote import VoteCreate, VotePublic

logger = logging.getLogger("pimpam.posts")

router = APIRouter(prefix="/posts", tags=["posts"])

_MAX_BODY_BYTES = 1_048_576  # 1 MB
_LINK_PREVIEW_UA = "PimPam/1.0 LinkPreview (+https://pimpam.org)"


class _OGParser(HTMLParser):
    """Minimal HTML parser that extracts OpenGraph meta tags and the <title>."""

    def __init__(self) -> None:
        super().__init__()
        self.og: dict[str, str] = {}
        self.title: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []
        self._head_done = False

    # ------------------------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._head_done:
            return
        if tag == "title":
            self._in_title = True
            self._title_parts = []
            return
        if tag == "meta":
            attr_map = {k.lower(): v for k, v in attrs if v is not None}
            prop = attr_map.get("property", "")
            if prop.startswith("og:") and "content" in attr_map:
                key = prop[3:]  # strip "og:" prefix
                self.og.setdefault(key, attr_map["content"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = "".join(self._title_parts).strip() or None
        if tag == "head":
            self._head_done = True

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create(
    request: Request, data: PostCreate, current_user: CurrentUser, db: DBSession
):
    """Create a new post, optionally within a community."""
    effective = (
        data.image_urls
        if data.image_urls
        else ([data.image_url] if data.image_url else [])
    )
    if len(effective) > 1 and not settings.multi_image_posts_enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Multiple images per post is not enabled",
        )
    if effective and len(effective) > settings.post_max_images:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.post_max_images} images per post",
        )

    if data.visibility == "group":
        group = await get_group(db, data.friend_group_id)
        if group is None or group.owner_id != current_user.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your group")

    post = await create_post(db, data, author_id=current_user.id)

    if post.visibility == "public":
        await index_post(post)

        # Notify local followers in real time
        follower_ids = await get_local_follower_ids(db, current_user.id)
        for fid in follower_ids:
            await publish_to_user(
                fid,
                "new_post",
                {
                    "id": post.id,
                    "title": post.title,
                    "author": current_user.username,
                },
            )

        if settings.federation_enabled:
            try:
                inboxes = await get_remote_follower_inboxes(db, current_user.id)
                if inboxes:
                    activity = build_create(post, current_user)
                    await deliver_activity(activity, current_user, inboxes)
            except Exception:
                logger.exception(
                    "Failed to deliver federation activity for post %s", post.id
                )

    return await annotate_post_with_user_vote(db, post, current_user.id)


@router.get("/link-preview", response_model=LinkPreview)
@limiter.limit("30/minute")
async def link_preview(
    request: Request,
    current_user: CurrentUser,
    url: str = Query(..., description="URL to fetch OpenGraph metadata from"),
) -> LinkPreview:
    """Fetch OpenGraph metadata from a URL and return a link preview."""
    empty = LinkPreview(url=url)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0),
            max_redirects=3,
            follow_redirects=True,
            headers={"User-Agent": _LINK_PREVIEW_UA},
        ) as http:
            response = await http.get(url)
    except (httpx.HTTPError, ValueError):
        return empty

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type:
        return empty

    # Limit body to 1 MB
    body = response.content[:_MAX_BODY_BYTES]
    try:
        html_text = body.decode("utf-8", errors="replace")
    except Exception:
        return empty

    parser = _OGParser()
    try:
        parser.feed(html_text)
    except Exception:
        return empty

    return LinkPreview(
        url=url,
        title=parser.og.get("title") or parser.title,
        description=parser.og.get("description"),
        image=parser.og.get("image"),
        site_name=parser.og.get("site_name"),
    )


@router.get("/{post_id}", response_model=PostPublic)
async def get(post_id: int, db: DBSession, current_user: OptionalUser = None):
    """Fetch a single post by ID. Removed posts are hidden unless you are a moderator."""
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.visibility == "group":
        viewer_id = current_user.id if current_user else None
        if viewer_id is None or (
            post.author_id != viewer_id
            and not await is_member(db, post.friend_group_id, viewer_id)
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Not authorised to view this post"
            )
    user_id = current_user.id if current_user else None
    return await annotate_post_with_user_vote(db, post, user_id)


@router.patch("/{post_id}", response_model=PostPublic)
@limiter.limit("20/minute")
async def edit(
    request: Request,
    post_id: int,
    data: PostUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Edit a post. Only the author may edit, and only within 1 hour of posting.
    The edit is flagged publicly (is_edited=True) but the edit history is not stored.
    After the 1-hour window, the post can only be deleted.
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")
    try:
        post = await edit_post(db, post, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e))
    await index_post(post)
    return await annotate_post_with_user_vote(db, post, current_user.id)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(post_id: int, current_user: CurrentUser, db: DBSession):
    """Delete a post. Only the author may delete their own post."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")
    await deindex_post(post_id)
    await delete_post(db, post)


@router.post("/{post_id}/vote", response_model=VotePublic)
@limiter.limit("30/minute")
async def vote(
    request: Request,
    post_id: int,
    data: VoteCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Cast or change a vote on a post (+1 or -1).
    You cannot vote on your own post — authors receive an automatic +1 at post creation.
    Changing an existing vote updates it and adjusts karma accordingly.
    """
    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot vote on your own post"
        )

    vote_obj = await cast_vote(db, current_user.id, post, data.direction)

    # Grouped vote notification for post author
    try:
        from app.crud.notification import notify as _notify

        await _notify(
            db,
            post.author_id,
            "vote",
            actor_id=current_user.id,
            post_id=post_id,
            group_key=f"vote:post:{post_id}",
        )
    except Exception:
        logger.exception("Failed to send vote notification for post %s", post_id)

    author = await get_user_by_id(db, post.author_id)
    await publish_to_user(
        post.author_id,
        "karma_update",
        {
            "post_id": post_id,
            "post_karma": post.karma,
            "user_karma": author.karma if author else None,
        },
    )

    # Send AP Like for +1 votes on federated posts
    if settings.federation_enabled and data.direction == 1 and post.ap_id:
        try:
            author = await get_user_by_id(db, post.author_id)
            if author and author.ap_inbox:
                activity = build_like(current_user.username, post.ap_id)
                await deliver_activity(activity, current_user, [author.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Like for post %s", post_id)

    return vote_obj


@router.delete("/{post_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def retract(
    request: Request, post_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Retract your vote on a post.
    You cannot retract the author's automatic initial vote.
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Cannot retract your author vote"
        )

    try:
        await retract_vote(db, current_user.id, post)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No vote to retract")

    author = await get_user_by_id(db, post.author_id)
    await publish_to_user(
        post.author_id,
        "karma_update",
        {
            "post_id": post_id,
            "post_karma": post.karma,
            "user_karma": author.karma if author else None,
        },
    )

    # Send AP Undo{Like} for federated posts
    if settings.federation_enabled and post.ap_id:
        try:
            author = await get_user_by_id(db, post.author_id)
            if author and author.ap_inbox:
                activity = build_undo_like(current_user.username, post.ap_id)
                await deliver_activity(activity, current_user, [author.ap_inbox])
        except Exception:
            logger.exception("Failed to deliver AP Undo{Like} for post %s", post_id)


@router.post("/{post_id}/boost", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def boost(
    request: Request, post_id: int, current_user: CurrentUser, db: DBSession
):
    """
    Boost (Announce) a federated post to your followers.
    Only works for posts that originated from a remote server (have an ap_id).
    When federation is disabled, returns 503.
    """
    if not settings.federation_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="Federation is disabled"
        )

    post = await get_post(db, post_id)
    if post is None or post.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not post.ap_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Cannot boost a local post over federation",
        )

    try:
        inboxes = await get_remote_follower_inboxes(db, current_user.id)
        if inboxes:
            activity = build_announce(current_user.username, post.ap_id)
            await deliver_activity(activity, current_user, inboxes)
    except Exception:
        logger.exception("Failed to deliver AP Announce for post %s", post_id)


@router.post(
    "/{post_id}/share", response_model=PostPublic, status_code=status.HTTP_201_CREATED
)
@limiter.limit("20/minute")
async def share(
    request: Request,
    post_id: int,
    data: ShareCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Reshare a post to your followers (and optionally into a community).
    The share appears as a new post authored by you, preserving a reference to the original.
    You can only share a given post once. Sharing a share is not allowed — the original is linked instead.
    """
    original = await get_post(db, post_id)
    if original is None or original.is_removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if original.visibility != "public":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot share a group post"
        )
    if original.author_id == current_user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Cannot share your own post"
        )

    try:
        post = await create_share(db, original, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(e))

    # Notify the original post author
    try:
        from app.crud.notification import notify as _notify

        await _notify(
            db,
            original.author_id,
            "share",
            actor_id=current_user.id,
            post_id=original.id,
        )
    except Exception:
        logger.exception("Failed to send share notification for post %s", original.id)

    # Notify local followers
    follower_ids = await get_local_follower_ids(db, current_user.id)
    for fid in follower_ids:
        await publish_to_user(
            fid,
            "new_post",
            {
                "id": post.id,
                "title": post.title,
                "author": current_user.username,
                "shared_from_id": post.shared_from_id,
            },
        )

    return await annotate_post_with_user_vote(db, post, current_user.id)
