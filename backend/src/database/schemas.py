from pydantic import BaseModel
from typing import List, Optional

# --- POST SCHEMAS ---
class PostBase(BaseModel):
    content: str

class PostCreate(PostBase):
    user_id: int

class Post(PostBase):
    id: int
    user_id: int
    class Config:
        orm_mode = True

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    username: str
    bio: Optional[str] = None

class UserCreate(UserBase):
    pass  # Add password here later

class User(UserBase):
    id: int
    posts: List[Post] = []
    class Config:
        orm_mode = True