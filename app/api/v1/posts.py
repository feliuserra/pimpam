from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DBSession
from app.crud.post import create_post, delete_post, get_post
from app.schemas.post import PostCreate, PostPublic

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
async def create(data: PostCreate, current_user: CurrentUser, db: DBSession):
    """Create a new post, optionally within a community."""
    return await create_post(db, data, author_id=current_user.id)


@router.get("/{post_id}", response_model=PostPublic)
async def get(post_id: int, db: DBSession):
    """Fetch a single post by ID."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(post_id: int, current_user: CurrentUser, db: DBSession):
    """Delete a post. Only the author may delete their own post."""
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your post")
    await delete_post(db, post)
