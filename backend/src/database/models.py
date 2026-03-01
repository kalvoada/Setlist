from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    bio = Column(String, nullable=True, default="")

    # Relationship to posts
    posts = relationship("DBPost", back_populates="author")
    comments = relationship("DBComment", back_populates="author")


class DBPost(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Relationship back to user
    author = relationship("DBUser", back_populates="posts")
    comments = relationship("DBComment", back_populates="post")

class DBComment(Base):
    __tablename__ = "comments"

    id      = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    author = relationship("DBUser", back_populates="comments")
    post   = relationship("DBPost", back_populates="comments")