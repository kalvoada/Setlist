"""Posts (always music), the timelines that list them, and likes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from .. import music as music_links
from .. import presenters
from ..database import models, schemas
from ..database.crud import comments as comments_crud
from ..database.crud import likes as likes_crud
from ..database.crud import posts as posts_crud
from ..dependencies import CurrentUser, DBSession, OptionalUser, PageParams

router = APIRouter(prefix="/posts", tags=["posts"])


def _get_post_or_404(db, post_id: int) -> models.DBPost:
    post = posts_crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def _parse_link(url: str) -> music_links.MusicLink:
    try:
        return music_links.parse_music_url(url)
    except music_links.UnsupportedMusicLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ── Composing ─────────────────────────────────────────────────────────────────
@router.post("/resolve-link", response_model=schemas.MusicLinkPreview)
def resolve_link(payload: schemas.LinkResolveRequest, _: CurrentUser):
    """Preview a pasted streaming link before posting it."""
    link = _parse_link(payload.url)
    metadata = music_links.fetch_metadata(link)
    return schemas.MusicLinkPreview(
        provider=link.provider.value,
        provider_name=music_links.PROVIDER_DISPLAY_NAMES[link.provider],
        item_type=link.item_type.value,
        url=link.url,
        title=(metadata.title or "").strip() or music_links.fallback_title(link),
        artist_name=metadata.artist_name,
        artwork_url=metadata.artwork_url,
        preview_url=metadata.preview_url,
    )


@router.post("/", response_model=schemas.Post, status_code=status.HTTP_201_CREATED)
def create_post(payload: schemas.PostCreate, current_user: CurrentUser, db: DBSession):
    """Create a post. A valid music link is required — captions alone are not."""
    link = _parse_link(payload.music_url)

    metadata = music_links.MusicMetadata(
        title=payload.title,
        artist_name=payload.artist_name,
        artwork_url=payload.artwork_url,
        preview_url=payload.preview_url,
    )
    if not metadata.title:
        # The client did not pre-resolve the link, so look it up now.
        metadata = music_links.fetch_metadata(link)

    music_item = posts_crud.get_or_create_music_item(db, link, metadata)
    post = posts_crud.create_post(
        db, author=current_user, music_item=music_item, caption=payload.caption
    )
    return presenters.post_out(db, post, current_user)


# ── Timelines ─────────────────────────────────────────────────────────────────
@router.get("/", response_model=schemas.Page[schemas.Post])
def read_posts(db: DBSession, viewer: OptionalUser, page: PageParams):
    """Discover: every post, newest first."""
    posts, total = posts_crud.list_posts(db, limit=page.limit, offset=page.offset)
    return presenters.page(
        presenters.posts_out(db, posts, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/feed", response_model=schemas.Page[schemas.Post])
def read_feed(current_user: CurrentUser, db: DBSession, page: PageParams):
    """Home: posts from the people you follow, plus your own."""
    posts, total = posts_crud.list_feed_posts(
        db, current_user.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.posts_out(db, posts, current_user),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/liked", response_model=schemas.Page[schemas.Post])
def read_liked_posts(current_user: CurrentUser, db: DBSession, page: PageParams):
    posts, total = posts_crud.list_liked_posts(
        db, current_user.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.posts_out(db, posts, current_user),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


# ── A single post ─────────────────────────────────────────────────────────────
@router.get("/{post_id}", response_model=schemas.PostWithComments)
def read_post(post_id: int, db: DBSession, viewer: OptionalUser):
    post = _get_post_or_404(db, post_id)
    comments, _ = comments_crud.list_comments(db, post.id, limit=100)
    return presenters.post_with_comments(db, post, comments, viewer)


@router.patch("/{post_id}", response_model=schemas.Post)
def update_post(
    post_id: int, payload: schemas.PostUpdate, current_user: CurrentUser, db: DBSession
):
    post = _get_post_or_404(db, post_id)
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    post = posts_crud.update_post(db, post, payload.caption)
    return presenters.post_out(db, post, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, current_user: CurrentUser, db: DBSession):
    post = _get_post_or_404(db, post_id)
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You can only delete your own posts"
        )
    posts_crud.delete_post(db, post)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Likes ─────────────────────────────────────────────────────────────────────
def _like_state(db, post_id: int, user_id: int) -> schemas.LikeState:
    return schemas.LikeState(
        post_id=post_id,
        is_liked=likes_crud.is_liked(db, user_id, post_id),
        likes_count=likes_crud.likes_count(db, post_id),
    )


@router.post("/{post_id}/like", response_model=schemas.LikeState)
def like_post(post_id: int, current_user: CurrentUser, db: DBSession):
    post = _get_post_or_404(db, post_id)
    likes_crud.like(db, current_user.id, post.id)
    return _like_state(db, post.id, current_user.id)


@router.delete("/{post_id}/like", response_model=schemas.LikeState)
def unlike_post(post_id: int, current_user: CurrentUser, db: DBSession):
    post = _get_post_or_404(db, post_id)
    likes_crud.unlike(db, current_user.id, post.id)
    return _like_state(db, post.id, current_user.id)


@router.get("/{post_id}/likes", response_model=schemas.Page[schemas.UserSummary])
def read_likers(post_id: int, db: DBSession, viewer: OptionalUser, page: PageParams):
    post = _get_post_or_404(db, post_id)
    users, total = likes_crud.list_likers(
        db, post.id, limit=page.limit, offset=page.offset
    )
    return presenters.page(
        presenters.user_summaries(db, users, viewer),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
