from pydantic import BaseModel
from typing import List, Optional

# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str
    user_id: int

class Comment(BaseModel):
    id:      int
    content: str
    user_id: int
    post_id: int

    model_config = {"from_attributes": True}

# ── Posts ─────────────────────────────────────────────────────────────────────
class PostCreate(BaseModel):
    content: str
    user_id: int

class Post(BaseModel):
    id: int
    user_id: int

    model_config = {"from_attributes": True}

class PostWithComments(Post):
    comments: List[Comment] = []

# ── Users ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    bio: Optional[str] = ""

class User(BaseModel):
    id:       int
    username: str
    bio:      Optional[str] = ""
    posts:    List[Post] = []

    model_config = {"from_attributes": True}

