from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import crud, models, schemas, database

router = APIRouter(
    prefix="/posts",
    tags=["posts"]
)

# --- Create a Post ---
@router.post("/", response_model=schemas.Post)
def create_post(post: schemas.PostCreate, db: Session = Depends(database.get_db)):
    return crud.create_post(db=db, post=post)

# --- Get All Posts ---
@router.get("/", response_model=List[schemas.Post])
def read_posts(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    posts = crud.get_posts(db, skip=skip, limit=limit)
    return posts