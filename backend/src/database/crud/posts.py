"""Post and music-item persistence."""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ... import music as music_links
from .. import models


def get_or_create_music_item(
    db: Session,
    link: music_links.MusicLink,
    metadata: music_links.MusicMetadata,
) -> models.DBMusicItem:
    """One row per (provider, item) — shared by every post about that item."""
    stmt = select(models.DBMusicItem).where(
        models.DBMusicItem.provider == link.provider.value,
        models.DBMusicItem.provider_item_id == link.provider_item_id,
    )
    item = db.scalars(stmt).first()

    title = (metadata.title or "").strip() or music_links.fallback_title(link)

    if item is None:
        item = models.DBMusicItem(
            provider=link.provider.value,
            item_type=link.item_type.value,
            provider_item_id=link.provider_item_id,
            url=link.url,
            title=title[:300],
            artist_name=(metadata.artist_name or None),
            artwork_url=(metadata.artwork_url or None),
            preview_url=(metadata.preview_url or None),
        )
        db.add(item)
        db.flush()
        return item

    # Backfill anything we learned since the item was first stored.
    if metadata.title and item.title != metadata.title:
        item.title = metadata.title[:300]
    if metadata.artist_name and not item.artist_name:
        item.artist_name = metadata.artist_name
    if metadata.artwork_url and not item.artwork_url:
        item.artwork_url = metadata.artwork_url
    if metadata.preview_url and not item.preview_url:
        item.preview_url = metadata.preview_url
    return item


def create_post(
    db: Session,
    *,
    author: models.DBUser,
    music_item: models.DBMusicItem,
    caption: str = "",
) -> models.DBPost:
    post = models.DBPost(
        caption=(caption or "").strip(),
        user_id=author.id,
        music_item_id=music_item.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_post(db: Session, post_id: int) -> Optional[models.DBPost]:
    stmt = (
        select(models.DBPost)
        .options(joinedload(models.DBPost.author), joinedload(models.DBPost.music))
        .where(models.DBPost.id == post_id)
    )
    return db.scalars(stmt).first()


def update_post(db: Session, post: models.DBPost, caption: str) -> models.DBPost:
    post.caption = (caption or "").strip()
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, post: models.DBPost) -> None:
    db.delete(post)
    db.commit()


def _base_query():
    return select(models.DBPost).options(
        joinedload(models.DBPost.author), joinedload(models.DBPost.music)
    )


def _paginate(
    db: Session, stmt, count_stmt, *, limit: int, offset: int
) -> tuple[List[models.DBPost], int]:
    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(models.DBPost.created_at.desc(), models.DBPost.id.desc())
    posts = list(db.scalars(stmt.limit(limit).offset(offset)).all())
    return posts, total


def list_posts(
    db: Session, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBPost], int]:
    """Discover timeline: everything, newest first."""
    return _paginate(
        db,
        _base_query(),
        select(func.count()).select_from(models.DBPost),
        limit=limit,
        offset=offset,
    )


def list_feed_posts(
    db: Session, user_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBPost], int]:
    """Home timeline: posts from people the user follows, plus their own."""
    following = select(models.DBFollow.following_id).where(
        models.DBFollow.follower_id == user_id
    )
    condition = or_(
        models.DBPost.user_id.in_(following),
        models.DBPost.user_id == user_id,
    )
    return _paginate(
        db,
        _base_query().where(condition),
        select(func.count()).select_from(models.DBPost).where(condition),
        limit=limit,
        offset=offset,
    )


def list_user_posts(
    db: Session, user_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBPost], int]:
    condition = models.DBPost.user_id == user_id
    return _paginate(
        db,
        _base_query().where(condition),
        select(func.count()).select_from(models.DBPost).where(condition),
        limit=limit,
        offset=offset,
    )


def list_liked_posts(
    db: Session, user_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBPost], int]:
    liked = select(models.DBLike.post_id).where(models.DBLike.user_id == user_id)
    condition = models.DBPost.id.in_(liked)
    return _paginate(
        db,
        _base_query().where(condition),
        select(func.count()).select_from(models.DBPost).where(condition),
        limit=limit,
        offset=offset,
    )


def comments_count_map(db: Session, post_ids: Sequence[int]) -> dict[int, int]:
    if not post_ids:
        return {}
    rows = db.execute(
        select(models.DBComment.post_id, func.count())
        .where(models.DBComment.post_id.in_(post_ids))
        .group_by(models.DBComment.post_id)
    ).all()
    return {post_id: count for post_id, count in rows}
