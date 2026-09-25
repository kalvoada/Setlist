"""
Five well-known songs against the real services, in every direction.

Off by default. Run it with network access and SPOTIFY_CLIENT_ID and
SPOTIFY_CLIENT_SECRET in .env:

    SETLIST_LIVE_TESTS=1 pytest tests/test_live_matching.py -v -s

Each case finds the song on the source service the way a listener would, then
asks Setlist for it on the target. A failure's captured log lists what the
target service offered instead.
"""

from __future__ import annotations

import functools
import itertools
import logging
import os
import time

import pytest

from src import music
from src.config import Settings
from src.music import ItemType, MusicMetadata, Provider

pytestmark = pytest.mark.skipif(
    os.environ.get("SETLIST_LIVE_TESTS") != "1",
    reason="calls the real services; set SETLIST_LIVE_TESTS=1",
)

SONGS = [
    ("Come Together", "The Beatles"),
    ("Bohemian Rhapsody", "Queen"),
    ("Billie Jean", "Michael Jackson"),
    ("Smells Like Teen Spirit", "Nirvana"),
    ("Blinding Lights", "The Weeknd"),
]


@pytest.fixture(autouse=True)
def real_services(monkeypatch, caplog):
    # conftest turns lookups off for the other tests; this one wants them.
    real = Settings()
    monkeypatch.setattr(music.settings, "enable_link_metadata", True)
    monkeypatch.setattr(music.settings, "spotify_client_id", real.spotify_client_id)
    monkeypatch.setattr(
        music.settings, "spotify_client_secret", real.spotify_client_secret
    )
    caplog.set_level(logging.INFO, logger="src.music")
    yield
    # Apple's API allows about 20 calls a minute.
    time.sleep(3)


@functools.cache
def find(service: Provider, title: str, artist: str) -> str:
    """The song's link on ``service``, found by searching for it."""
    reference = MusicMetadata(title=title, artist_name=artist)
    _, search = music._CATALOGUES[service]
    with music._client() as client:
        candidates = search(client, ItemType.TRACK, reference)
    link = music.best_match(reference, ItemType.TRACK, candidates)
    assert link, f"{title} by {artist} isn't on {service.value}: " + str(
        [(m.title, m.artist_name) for _, m in candidates[:5]]
    )
    return link.url


@pytest.mark.parametrize(
    ("title", "artist", "source", "target"),
    [
        pytest.param(title, artist, source, target,
                     id=f"{title}: {source.value} -> {target.value}")
        for title, artist in SONGS
        for source, target in itertools.permutations(music.NATIVE_PROVIDERS, 2)
    ],
)
def test_song_opens_on_the_other_service(title, artist, source, target):
    url = find(source, title, artist)

    resolved = music.resolve_link(url, target)

    print(f"\n  {source.value}: {url}\n  {target.value}: {resolved}")
    assert resolved, f"{url} has no match on {target.value}; see the captured log"
    link = music.parse_music_url(resolved)
    assert link.provider is target
    assert link.item_type is ItemType.TRACK
