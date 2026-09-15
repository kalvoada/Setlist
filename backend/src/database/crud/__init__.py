"""Data-access layer.

Split by aggregate so routers stay thin; import as ``from ..database import crud``
and call ``crud.users.get_user(...)``.
"""

from . import comments, follows, likes, posts, users

__all__ = ["comments", "follows", "likes", "posts", "users"]
