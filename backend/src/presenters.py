"""Turn ORM rows into API payloads.

Counts and viewer-specific flags (``is_liked``, ``is_following``) are resolved
in batches so a page of posts costs a fixed number of queries instead of one
per row.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from . import music as music_links
from .database import crud, models, schemas


def provider_name(provider: str) -> str:
    try:
        return music_links.PROVIDER_DISPLAY_NAMES[music_links.Provider(provider)]
    except ValueError:
        return provider.replace("_", " ").title()


def music_item(item: models.DBMusicItem) -> schemas.MusicItem:
    return schemas.MusicItem(
        id=item.id,
        provider=item.provider,
        provider_name=provider_name(item.provider),
        item_type=item.item_type,
        url=item.url,
        title=item.title,
        artist_name=item.artist_name,
        artwork_url=item.artwork_url,
        preview_url=item.preview_url,
    )


def user_public(user: models.DBUser) -> schemas.UserPublic:
    return schemas.UserPublic(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        bio=user.bio or "",
    )


def user_summaries(
    db: Session,
    users: Sequence[models.DBUser],
    viewer: Optional[models.DBUser],
) -> List[schemas.UserSummary]:
    user_ids = [user.id for user in users]
    followers = crud.follows.followers_count_map(db, user_ids)
    following = crud.follows.following_count_map(db, user_ids)
    posts = crud.users.posts_count_map(db, user_ids)

    viewer_follows: set[int] = set()
    follows_viewer: set[int] = set()
    if viewer is not None:
        viewer_follows = crud.follows.followed_subset(db, viewer.id, user_ids)
        follows_viewer = crud.follows.follower_subset(db, viewer.id, user_ids)

    return [
        schemas.UserSummary(
            **user_public(user).model_dump(),
            followers_count=followers.get(user.id, 0),
            following_count=following.get(user.id, 0),
            posts_count=posts.get(user.id, 0),
            is_following=user.id in viewer_follows,
            is_followed_by=user.id in follows_viewer,
            is_me=viewer is not None and viewer.id == user.id,
        )
        for user in users
    ]


def user_summary(
    db: Session, user: models.DBUser, viewer: Optional[models.DBUser]
) -> schemas.UserSummary:
    return user_summaries(db, [user], viewer)[0]


def user_profile(
    db: Session, user: models.DBUser, viewer: Optional[models.DBUser]
) -> schemas.UserProfile:
    summary = user_summary(db, user, viewer)
    return schemas.UserProfile(**summary.model_dump(), created_at=user.created_at)


def current_user(db: Session, user: models.DBUser) -> schemas.CurrentUser:
    profile = user_profile(db, user, user)
    return schemas.CurrentUser(**profile.model_dump(), email=user.email)


def posts_out(
    db: Session,
    posts: Sequence[models.DBPost],
    viewer: Optional[models.DBUser],
) -> List[schemas.Post]:
    post_ids = [post.id for post in posts]
    likes = crud.likes.likes_count_map(db, post_ids)
    comments = crud.posts.comments_count_map(db, post_ids)
    liked = (
        crud.likes.liked_subset(db, viewer.id, post_ids) if viewer is not None else set()
    )

    return [
        schemas.Post(
            id=post.id,
            caption=post.caption or "",
            created_at=post.created_at,
            author=user_public(post.author),
            music=music_item(post.music),
            likes_count=likes.get(post.id, 0),
            comments_count=comments.get(post.id, 0),
            is_liked=post.id in liked,
        )
        for post in posts
    ]


def post_out(
    db: Session, post: models.DBPost, viewer: Optional[models.DBUser]
) -> schemas.Post:
    return posts_out(db, [post], viewer)[0]


def post_with_comments(
    db: Session,
    post: models.DBPost,
    comments: Sequence[models.DBComment],
    viewer: Optional[models.DBUser],
) -> schemas.PostWithComments:
    return schemas.PostWithComments(
        **post_out(db, post, viewer).model_dump(),
        comments=[comment_out(comment) for comment in comments],
    )


def comment_out(comment: models.DBComment) -> schemas.Comment:
    return schemas.Comment(
        id=comment.id,
        content=comment.content,
        post_id=comment.post_id,
        created_at=comment.created_at,
        author=user_public(comment.author),
    )


def page(items: list, *, total: int, limit: int, offset: int) -> dict:
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": total,
        "has_more": offset + len(items) < total,
    }
