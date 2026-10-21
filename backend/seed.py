"""
Populate a development database with realistic Setlist data.

    python seed.py            # rebuild ./social.db from scratch
    DATABASE_URL=... python seed.py

WARNING: this drops every table first
"""

from __future__ import annotations

import random

from sqlalchemy import text

from src import music
from src.config import settings
from src.database.crud import posts as posts_crud
from src.database.database import Base, SessionLocal, engine
from src.database.migrate import upgrade_database
from src.database.models import (
    DBComment,
    DBFollow,
    DBLike,
    DBPost,
    DBUser,
)
from src.security import hash_password

DEMO_PASSWORD = "setlist123"

USERS = [
    ("adam", "adam@setlist.app", "Adam Kalvoda", "Building Setlist. Mostly shoegaze."),
    ("mia", "mia@setlist.app", "Mia Novak", "Vinyl only. Fight me."),
    ("dusan", "dusan@setlist.app", "Dušan Knop", "Techno and long walks."),
    ("lena", "lena@setlist.app", "Lena Fischer", "Jazz piano, badly."),
    ("tomas", "tomas@setlist.app", "Tomáš Bažant", "Playlist curator, allegedly."),
    ("nora", "nora@setlist.app", "Nora Sedláková", "90s hip hop enjoyer."),
]

# Spotify, Apple Music and YouTube Music links are found by searching the real
# catalogues when seeding, so they point at songs that exist. That needs network
# access (and SPOTIFY_CLIENT_ID/SECRET for Spotify); anything not found is skipped.
MUSIC = [
    ("spotify", "track", "Never Gonna Give You Up", "Rick Astley"),
    ("apple_music", "track", "Come Together", "The Beatles"),
    ("youtube_music", "track", "Smells Like Teen Spirit", "Nirvana"),
    ("spotify", "track", "Blinding Lights", "The Weeknd"),
    ("apple_music", "track", "Bohemian Rhapsody", "Queen"),
    ("youtube_music", "track", "Billie Jean", "Michael Jackson"),
    ("spotify", "album", "Abbey Road", "The Beatles"),
    ("apple_music", "album", "Kind of Blue", "Miles Davis"),
]

# SoundCloud and Bandcamp can't be searched here, so these links are fixed.
FIXED_MUSIC = [
    ("https://soundcloud.com/forss/flickermood", "Flickermood", "Forss"),
    ("https://c418.bandcamp.com/album/minecraft-volume-alpha", "Minecraft - Volume Alpha",
     "C418"),
]

CAPTIONS = [
    "On repeat all week.",
    "This bridge does something to my brain.",
    "Perfect for the tram ride home.",
    "Still the best thing they ever recorded.",
    "Turn it up loud.",
    "Found this at 2am, no regrets.",
    "",
    "Album of the year, calling it now.",
]

COMMENTS = [
    "This is a certified banger.",
    "Adding to my evening playlist.",
    "How have I never heard this?",
    "Saw them live last year — unreal.",
    "The drums on this!",
    "Respectfully, no.",
    "Instant like.",
]


def find_music() -> list[tuple[music.MusicLink, music.MusicMetadata]]:
    found = []
    for provider, kind, title, artist in MUSIC:
        try:
            url = music.find_link(
                music.Provider(provider), music.ItemType(kind), title, artist
            ) if settings.enable_link_metadata else None
        except Exception as exc:  # noqa: BLE001 - offline, no credentials, ...
            print(f"  skipped {title} ({provider}): {exc}")
            continue
        if url is None:
            print(f"  skipped {title} ({provider}): not found")
            continue
        found.append((url, title, artist))

    music_found = []
    for url, title, artist in found + FIXED_MUSIC:
        link = music.parse_music_url(url)
        # Artwork, and Bandcamp's player id; never fails, worst case empty.
        metadata = music.fetch_metadata(link)
        metadata.title, metadata.artist_name = title, artist
        print(f"  {link.provider.value:14} {title}: {url}")
        music_found.append((link, metadata))
    return music_found


def main() -> None:
    print(f"Resetting {settings.database_url} ...")
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    upgrade_database()

    random.seed(7)
    db = SessionLocal()

    try:
        print("Creating users ...")
        users = [
            DBUser(
                username=username,
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                bio=bio,
            )
            for username, email, display_name, bio in USERS
        ]
        db.add_all(users)
        db.commit()

        print("Finding the music ...")
        music_items = [
            posts_crud.get_or_create_music_item(db, link, metadata)
            for link, metadata in find_music()
        ]
        db.commit()

        print("Creating posts ...")
        posts = []
        for index, item in enumerate(music_items):
            for author in random.sample(users, k=random.randint(1, 3)):
                posts.append(
                    DBPost(
                        caption=CAPTIONS[(index + author.id) % len(CAPTIONS)],
                        user_id=author.id,
                        music_item_id=item.id,
                    )
                )
        db.add_all(posts)
        db.commit()

        print("Creating follows ...")
        follows = set()
        for follower in users:
            for following in random.sample(users, k=3):
                if follower.id != following.id:
                    follows.add((follower.id, following.id))
        db.add_all(
            DBFollow(follower_id=follower_id, following_id=following_id)
            for follower_id, following_id in follows
        )
        db.commit()

        print("Creating likes and comments ...")
        likes = set()
        comments = []
        for post in posts:
            for user in random.sample(users, k=random.randint(0, 4)):
                likes.add((user.id, post.id))
            for user in random.sample(users, k=random.randint(0, 2)):
                comments.append(
                    DBComment(
                        content=random.choice(COMMENTS),
                        user_id=user.id,
                        post_id=post.id,
                    )
                )
        db.add_all(DBLike(user_id=user_id, post_id=post_id) for user_id, post_id in likes)
        db.add_all(comments)
        db.commit()

        print(
            f"Seeded {len(users)} users, {len(posts)} posts, {len(follows)} follows, "
            f"{len(likes)} likes and {len(comments)} comments."
        )
        print(f"Sign in with any username above and the password {DEMO_PASSWORD!r}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
