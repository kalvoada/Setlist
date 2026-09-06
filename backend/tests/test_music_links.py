"""Streaming-link parsing."""

import pytest

from src.music import ItemType, Provider, UnsupportedMusicLinkError, parse_music_url


@pytest.mark.parametrize(
    ("url", "provider", "item_type", "item_id"),
    [
        (
            "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=abc",
            Provider.SPOTIFY,
            ItemType.TRACK,
            "4cOdK2wGLETKBW3PvgPWqT",
        ),
        (
            "https://open.spotify.com/intl-de/album/1DFixLWuPkv3KT3TnV35m3",
            Provider.SPOTIFY,
            ItemType.ALBUM,
            "1DFixLWuPkv3KT3TnV35m3",
        ),
        ("spotify:playlist:37i9dQZF1DX", Provider.SPOTIFY, ItemType.PLAYLIST, "37i9dQZF1DX"),
        (
            "https://music.apple.com/us/album/abbey-road/1474815798?i=1474815817",
            Provider.APPLE_MUSIC,
            ItemType.TRACK,
            "1474815817",
        ),
        (
            "https://music.apple.com/gb/playlist/todays-hits/pl.f4d106fed2bd",
            Provider.APPLE_MUSIC,
            ItemType.PLAYLIST,
            "pl.f4d106fed2bd",
        ),
        (
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            Provider.YOUTUBE_MUSIC,
            ItemType.TRACK,
            "dQw4w9WgXcQ",
        ),
        ("https://youtu.be/dQw4w9WgXcQ", Provider.YOUTUBE_MUSIC, ItemType.TRACK, "dQw4w9WgXcQ"),
        (
            "https://soundcloud.com/artist/sets/demo",
            Provider.SOUNDCLOUD,
            ItemType.PLAYLIST,
            "artist/sets/demo",
        ),
        ("https://tidal.com/browse/track/12345", Provider.TIDAL, ItemType.TRACK, "12345"),
        ("https://www.deezer.com/en/track/3135556", Provider.DEEZER, ItemType.TRACK, "3135556"),
    ],
)
def test_supported_links(url, provider, item_type, item_id):
    link = parse_music_url(url)
    assert link.provider is provider
    assert link.item_type is item_type
    assert link.provider_item_id == item_id


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "hello world",
        "https://example.com/song.mp3",
        "ftp://open.spotify.com/track/abc",
        "https://open.spotify.com/",
        "https://music.apple.com/us/",
    ],
)
def test_rejected_links(url):
    with pytest.raises(UnsupportedMusicLinkError):
        parse_music_url(url)


def test_tracking_parameters_are_stripped_from_spotify_links():
    link = parse_music_url("https://open.spotify.com/track/abc123?si=xyz&utm_source=copy")
    assert link.url == "https://open.spotify.com/track/abc123"
