"""Pydantic request/response models (the public shape of the API)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
)

T = TypeVar("T")

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9._]{1,28})[a-zA-Z0-9]$")
MIN_PASSWORD_LENGTH = 8


def _to_utc_iso(value: datetime) -> str:
    """Always hand clients an explicit UTC timestamp."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDatetime = Annotated[datetime, PlainSerializer(_to_utc_iso, return_type=str)]

ORM = ConfigDict(from_attributes=True)


def validate_username(value: str) -> str:
    value = (value or "").strip()
    if not USERNAME_PATTERN.match(value):
        raise ValueError(
            "Username must be 3-30 characters: letters, numbers, dots or "
            "underscores, starting and ending with a letter or number."
        )
    return value


def validate_password(value: str) -> str:
    if len(value or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    return value


# ── Pagination ────────────────────────────────────────────────────────────────
class Page(BaseModel, Generic[T]):
    items: List[T]
    limit: int
    offset: int
    total: int
    has_more: bool


# ── Auth ──────────────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: Optional[str] = Field(default=None, max_length=50)

    _v_username = field_validator("username")(validate_username)
    _v_password = field_validator("password")(validate_password)


class AuthResponse(Token):
    """Token plus the freshly authenticated user, so the client can render
    immediately after sign-in without a second round trip."""

    user: "CurrentUser"


class LoginRequest(BaseModel):
    """``identifier`` accepts either the username or the e-mail address."""

    identifier: str
    password: str


# ── Users ─────────────────────────────────────────────────────────────────────
class UserPublic(BaseModel):
    """The user shape embedded in posts, comments and lists."""

    model_config = ORM

    id: int
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: str = ""


class UserSummary(UserPublic):
    """A user in a list, with the social counters the UI shows."""

    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_following: bool = False
    is_followed_by: bool = False
    is_me: bool = False


class UserProfile(UserSummary):
    created_at: UTCDatetime


class CurrentUser(UserProfile):
    """The authenticated user — includes private fields."""

    email: EmailStr


class ProfileUpdate(BaseModel):
    """Editable profile fields (Settings › Edit profile)."""

    display_name: Optional[str] = Field(default=None, max_length=50)
    bio: Optional[str] = Field(default=None, max_length=300)
    avatar_url: Optional[str] = Field(default=None, max_length=500)


class AccountUpdate(BaseModel):
    """Editable account fields (Settings › Account). Requires the password."""

    current_password: str
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    new_password: Optional[str] = None

    @field_validator("username")
    @classmethod
    def _username(cls, value: Optional[str]) -> Optional[str]:
        return validate_username(value) if value is not None else None

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: Optional[str]) -> Optional[str]:
        return validate_password(value) if value is not None else None


class AccountDelete(BaseModel):
    current_password: str


class FollowState(BaseModel):
    user_id: int
    is_following: bool
    followers_count: int


# ── Music ─────────────────────────────────────────────────────────────────────
class MusicItem(BaseModel):
    model_config = ORM

    id: int
    provider: str
    provider_name: str = ""
    item_type: str
    url: str
    title: str
    artist_name: Optional[str] = None
    artwork_url: Optional[str] = None
    preview_url: Optional[str] = None


class MusicLinkPreview(BaseModel):
    """Result of resolving a pasted link before the post is created."""

    provider: str
    provider_name: str
    item_type: str
    url: str
    title: str
    artist_name: Optional[str] = None
    artwork_url: Optional[str] = None
    preview_url: Optional[str] = None


# ── Posts ─────────────────────────────────────────────────────────────────────
class PostCreate(BaseModel):
    """A post always carries music: ``music_url`` is required.

    The optional title/artist/artwork fields let the client pass through what it
    already resolved via ``POST /posts/resolve-link`` so the server does not
    have to hit the provider twice.
    """

    music_url: str = Field(min_length=4, max_length=500)
    caption: str = Field(default="", max_length=500)
    title: Optional[str] = Field(default=None, max_length=300)
    artist_name: Optional[str] = Field(default=None, max_length=300)
    artwork_url: Optional[str] = Field(default=None, max_length=500)
    preview_url: Optional[str] = Field(default=None, max_length=500)


class PostUpdate(BaseModel):
    caption: str = Field(max_length=500)


class LinkResolveRequest(BaseModel):
    url: str = Field(min_length=4, max_length=500)


class Post(BaseModel):
    id: int
    caption: str
    created_at: UTCDatetime
    author: UserPublic
    music: MusicItem
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False


class LikeState(BaseModel):
    post_id: int
    is_liked: bool
    likes_count: int


# ── Comments ──────────────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Comment cannot be empty.")
        return value


class Comment(BaseModel):
    id: int
    content: str
    post_id: int
    created_at: UTCDatetime
    author: UserPublic


class PostWithComments(Post):
    comments: List[Comment] = []


AuthResponse.model_rebuild()
