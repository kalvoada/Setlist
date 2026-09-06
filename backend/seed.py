"""Populate a development database with realistic Setlist data.

    python seed.py            # rebuild ./social.db from scratch
    DATABASE_URL=... python seed.py

WARNING: this drops every table first — never point it at production.
"""

from __future__ import annotations

import random

from src.config import settings
from src.database.database import Base, SessionLocal, engine
from src.database.models import (
    DBComment,
    DBFollow,
    DBLike,
    DBMusicItem,
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

MUSIC = [
    {
        "provider": "spotify",
        "item_type": "track",
        "provider_item_id": "4cOdK2wGLETKBW3PvgPWqT",
        "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
        "title": "Never Gonna Give You Up",
        "artist_name": "Rick Astley",
    },
    {
        "provider": "spotify",
        "item_type": "album",
        "provider_item_id": "1DFixLWuPkv3KT3TnV35m3",
        "url": "https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3",
        "title": "Melodrama",
        "artist_name": "Lorde",
    },
    {
        "provider": "spotify",
        "item_type": "playlist",
        "provider_item_id": "37i9dQZF1DXcBWIGoYBM5M",
        "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
        "title": "Today's Top Hits",
        "artist_name": "Spotify",
    },
    {
        "provider": "apple_music",
        "item_type": "track",
        "provider_item_id": "1474815817",
        "url": "https://music.apple.com/us/album/come-together/1474815798?i=1474815817",
        "title": "Come Together",
        "artist_name": "The Beatles",
    },
    {
        "provider": "apple_music",
        "item_type": "album",
        "provider_item_id": "1440857781",
        "url": "https://music.apple.com/us/album/kind-of-blue/1440857781",
        "title": "Kind of Blue",
        "artist_name": "Miles Davis",
    },
    {
        "provider": "youtube_music",
        "item_type": "track",
        "provider_item_id": "hTWKbfoikeg",
        "url": "https://music.youtube.com/watch?v=hTWKbfoikeg",
        "title": "Smells Like Teen Spirit",
        "artist_name": "Nirvana",
    },
    {
        "provider": "soundcloud",
        "item_type": "track",
        "provider_item_id": "flume/say-it",
        "url": "https://soundcloud.com/flume/say-it",
        "title": "Say It",
        "artist_name": "Flume",
    },
    {
        "provider": "tidal",
        "item_type": "album",
        "provider_item_id": "77640617",
        "url": "https://tidal.com/browse/album/77640617",
        "title": "In Rainbows",
        "artist_name": "Radiohead",
    },
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


def main() -> None:
    print(f"Resetting {settings.database_url} ...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

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

        print("Creating music items ...")
        music_items = [DBMusicItem(**item) for item in MUSIC]
        db.add_all(music_items)
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
