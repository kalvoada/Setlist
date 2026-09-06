"""Comment persistence."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .. import models


def get_comment(db: Session, comment_id: int) -> Optional[models.DBComment]:
    stmt = (
        select(models.DBComment)
        .options(joinedload(models.DBComment.author))
        .where(models.DBComment.id == comment_id)
    )
    return db.scalars(stmt).first()


def list_comments(
    db: Session, post_id: int, *, limit: int = 50, offset: int = 0
) -> tuple[List[models.DBComment], int]:
    total = db.scalar(
        select(func.count())
        .select_from(models.DBComment)
        .where(models.DBComment.post_id == post_id)
    ) or 0

    stmt = (
        select(models.DBComment)
        .options(joinedload(models.DBComment.author))
        .where(models.DBComment.post_id == post_id)
        .order_by(models.DBComment.created_at.asc(), models.DBComment.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all()), total


def create_comment(
    db: Session, *, post_id: int, author: models.DBUser, content: str
) -> models.DBComment:
    comment = models.DBComment(
        content=content.strip(), post_id=post_id, user_id=author.id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment: models.DBComment) -> None:
    db.delete(comment)
    db.commit()
