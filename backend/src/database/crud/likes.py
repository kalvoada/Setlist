"""Like persistence."""

from __future__ import annotations

from typing import List, Sequence, Set

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import models


def is_liked(db: Session, user_id: int, post_id: int) -> bool:
    stmt = select(func.count()).select_from(models.DBLike).where(
        models.DBLike.user_id == user_id, models.DBLike.post_id == post_id
    )
    return bool(db.scalar(stmt))


def like(db: Session, user_id: int, post_id: int) -> bool:
    """Idempotent: returns ``False`` when the post was already liked."""
    if is_liked(db, user_id, post_id):
        return False
    db.add(models.DBLike(user_id=user_id, post_id=post_id))
    db.commit()
    return True


def unlike(db: Session, user_id: int, post_id: int) -> bool:
    result = db.execute(
        delete(models.DBLike).where(
            models.DBLike.user_id == user_id, models.DBLike.post_id == post_id
        )
    )
    db.commit()
    return result.rowcount > 0


def likes_count(db: Session, post_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(models.DBLike)
        .where(models.DBLike.post_id == post_id)
    ) or 0


def likes_count_map(db: Session, post_ids: Sequence[int]) -> dict[int, int]:
    if not post_ids:
        return {}
    rows = db.execute(
        select(models.DBLike.post_id, func.count())
        .where(models.DBLike.post_id.in_(post_ids))
        .group_by(models.DBLike.post_id)
    ).all()
    return {post_id: count for post_id, count in rows}


def liked_subset(db: Session, user_id: int, post_ids: Sequence[int]) -> Set[int]:
    if not post_ids:
        return set()
    return set(
        db.scalars(
            select(models.DBLike.post_id).where(
                models.DBLike.user_id == user_id,
                models.DBLike.post_id.in_(post_ids),
            )
        ).all()
    )


def list_likers(
    db: Session, post_id: int, *, limit: int = 20, offset: int = 0
) -> tuple[List[models.DBUser], int]:
    total = likes_count(db, post_id)
    stmt = (
        select(models.DBUser)
        .join(models.DBLike, models.DBLike.user_id == models.DBUser.id)
        .where(models.DBLike.post_id == post_id)
        .order_by(models.DBLike.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all()), total
