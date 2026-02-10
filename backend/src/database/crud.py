from sqlalchemy.orm import Session
from . import models, schemas

# --- USER CRUD ---
def get_user(db: Session, user_id: int):
    return db.query(models.DBUser).filter(models.DBUser.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.DBUser(username=user.username, bio=user.bio)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- POST CRUD ---
def get_posts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DBPost).offset(skip).limit(limit).all()

def create_post(db: Session, post: schemas.PostCreate):
    db_post = models.DBPost(content=post.content, user_id=post.user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

# -- SEARCH CRUD ---
def search_users(db: Session, query: str):
    return db.query(models.DBUser).filter(models.DBUser.username.contains(query)).all()