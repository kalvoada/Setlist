from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import crud, models, schemas, database

router = APIRouter(prefix="/posts", tags=["comments"])


@router.get("/{post_id}/comments", response_model=List[schemas.Comment])
def get_comments(post_id: int, db: Session = Depends(database.get_db)):
    post = crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud.get_comments_for_post(db, post_id)


@router.post("/{post_id}/comments", response_model=schemas.Comment)
def create_comment(post_id: int, comment: schemas.CommentCreate, db: Session = Depends(database.get_db)):
    post = crud.get_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return crud.create_comment(db, post_id, comment)