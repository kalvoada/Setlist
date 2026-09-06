"""Setlist API — application entry point.

Run locally:  uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database.database import Base, engine
from src.routers import auth, comments, posts, users

DESCRIPTION = """
The backend for **Setlist**, a social app for sharing music.

* Sign up / sign in with a bearer token
* Follow people and read a feed of what they are listening to
* Post a song, album or playlist from Spotify, Apple Music, YouTube Music,
  SoundCloud, TIDAL, Deezer or Bandcamp — every post carries music
* Like and comment on posts
* Edit your profile and account settings
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(posts.router)
    app.include_router(comments.router)

    @app.get("/", tags=["meta"])
    def root():
        return {
            "service": settings.app_name,
            "version": app.version,
            "docs": "/docs",
        }

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "environment": settings.environment}

    if not settings.is_production:
        # Convenience for local development; production runs `alembic upgrade head`.
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
