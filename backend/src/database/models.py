"""SQLAlchemy ORM models for Setlist."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (portable across SQLite and Postgres)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DBUser(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    display_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bio: Mapped[str] = mapped_column(String(300), default="", server_default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    posts: Mapped[List["DBPost"]] = relationship(
        back_populates="author", cascade="all, delete-orphan", passive_deletes=True
    )
    comments: Mapped[List["DBComment"]] = relationship(
        back_populates="author", cascade="all, delete-orphan", passive_deletes=True
    )
    likes: Mapped[List["DBLike"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    # Rows where this user is the one doing the following.
    following: Mapped[List["DBFollow"]] = relationship(
        back_populates="follower",
        foreign_keys="DBFollow.follower_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    # Rows where this user is the one being followed.
    followers: Mapped[List["DBFollow"]] = relationship(
        back_populates="following",
        foreign_keys="DBFollow.following_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<DBUser id={self.id} username={self.username!r}>"


class DBFollow(Base):
    """Directed edge: ``follower_id`` follows ``following_id``."""

    __tablename__ = "follows"
    __table_args__ = (
        CheckConstraint("follower_id != following_id", name="ck_follows_no_self"),
        Index("ix_follows_following_id", "following_id"),
    )

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    follower: Mapped["DBUser"] = relationship(
        back_populates="following", foreign_keys=[follower_id]
    )
    following: Mapped["DBUser"] = relationship(
        back_populates="followers", foreign_keys=[following_id]
    )


class DBMusicItem(Base):
    """A song / album / playlist shared from a streaming provider.

    Stored once and referenced by every post that shares it, so the same track
    posted by ten people is one row.
    """

    __tablename__ = "music_items"
    __table_args__ = (
        UniqueConstraint("provider", "provider_item_id", name="uq_music_provider_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    item_type: Mapped[str] = mapped_column(String(20))
    provider_item_id: Mapped[str] = mapped_column(String(120))

    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300))
    artist_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    artwork_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    posts: Mapped[List["DBPost"]] = relationship(back_populates="music")


class DBPost(Base):
    """A shared music item plus an optional caption.

    ``music_item_id`` is NOT NULL on purpose: a Setlist post is always about a
    song, album or playlist — never a bare status update.
    """

    __tablename__ = "posts"
    __table_args__ = (Index("ix_posts_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    caption: Mapped[str] = mapped_column(Text, default="", server_default="")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    music_item_id: Mapped[int] = mapped_column(
        ForeignKey("music_items.id", ondelete="RESTRICT"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    author: Mapped["DBUser"] = relationship(back_populates="posts")
    music: Mapped["DBMusicItem"] = relationship(back_populates="posts")
    comments: Mapped[List["DBComment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )
    likes: Mapped[List["DBLike"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )


class DBLike(Base):
    __tablename__ = "likes"
    __table_args__ = (Index("ix_likes_post_id", "post_id"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["DBUser"] = relationship(back_populates="likes")
    post: Mapped["DBPost"] = relationship(back_populates="likes")


class DBComment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    author: Mapped["DBUser"] = relationship(back_populates="comments")
    post: Mapped["DBPost"] = relationship(back_populates="comments")
