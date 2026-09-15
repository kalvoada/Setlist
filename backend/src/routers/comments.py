"""Comments on posts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from .. import presenters
from ..database import schemas
from ..database.crud import comments as comments_crud
from ..database.crud import posts as posts_crud
from ..dependencies import CurrentUser, DBSession, OptionalUser, PageParams

router = APIRouter(tags=["comments"])


@router.get("/posts/{post_id}/comments", response_model=schemas.Page[schemas.Comment])
def read_comments(post_id: int, db: DBSession, _: OptionalUser, page: PageParams):
    if posts_crud.get_post(db, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comments, total = comments_crud.list_comments(
        db, post_id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        [presenters.comment_out(comment) for comment in comments],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "/posts/{post_id}/comments",
    response_model=schemas.Comment,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: int,
    payload: schemas.CommentCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    if posts_crud.get_post(db, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")

    comment = comments_crud.create_comment(
        db, post_id=post_id, author=current_user, content=payload.content
    )
    return presenters.comment_out(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, current_user: CurrentUser, db: DBSession):
    """A comment can be removed by its author or by the owner of the post."""
    comment = comments_crud.get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    post = posts_crud.get_post(db, comment.post_id)
    if comment.user_id != current_user.id and (
        post is None or post.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="You cannot delete this comment"
        )

    comments_crud.delete_comment(db, comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
