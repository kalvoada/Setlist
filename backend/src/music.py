"""Parsing and enrichment of streaming-service links.

A Setlist post always carries a piece of music, so this module turns a pasted
link ("share" from Spotify, Apple Music, …) into structured data we can store
and render. Metadata lookup is best-effort: the post must still succeed when a
provider is slow or unreachable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import parse_qs, urlparse

import httpx

from .config import settings


class Provider(str, Enum):
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    YOUTUBE_MUSIC = "youtube_music"
    SOUNDCLOUD = "soundcloud"
    TIDAL = "tidal"
    DEEZER = "deezer"
    BANDCAMP = "bandcamp"


class ItemType(str, Enum):
    TRACK = "track"
    ALBUM = "album"
    PLAYLIST = "playlist"
    ARTIST = "artist"


PROVIDER_DISPLAY_NAMES = {
    Provider.SPOTIFY: "Spotify",
    Provider.APPLE_MUSIC: "Apple Music",
    Provider.YOUTUBE_MUSIC: "YouTube Music",
    Provider.SOUNDCLOUD: "SoundCloud",
    Provider.TIDAL: "TIDAL",
    Provider.DEEZER: "Deezer",
    Provider.BANDCAMP: "Bandcamp",
}


@dataclass(frozen=True)
class MusicLink:
    """A streaming link resolved to the item it points at."""

    provider: Provider
    item_type: ItemType
    provider_item_id: str
    url: str


@dataclass
class MusicMetadata:
    title: Optional[str] = None
    artist_name: Optional[str] = None
    artwork_url: Optional[str] = None
    preview_url: Optional[str] = None


class UnsupportedMusicLinkError(ValueError):
    """Raised when a URL is not a recognisable music link."""


_SPOTIFY_TYPES = {
    "track": ItemType.TRACK,
    "album": ItemType.ALBUM,
    "playlist": ItemType.PLAYLIST,
    "artist": ItemType.ARTIST,
}

_SPOTIFY_URI = re.compile(r"^spotify:(track|album|playlist|artist):([A-Za-z0-9]+)$")
_SPOTIFY_PATH = re.compile(
    r"^/(?:intl-[a-z]{2}/)?(track|album|playlist|artist)/([A-Za-z0-9]+)"
)
_APPLE_PATH = re.compile(
    r"^/[a-z]{2}/(album|playlist|song|artist|music-video)/([^/]+)/([^/?#]+)"
)
_BANDCAMP_PATH = re.compile(r"^/(track|album)/([^/?#]+)")
_TIDAL_PATH = re.compile(r"^/(?:browse/)?(track|album|playlist|artist)/([^/?#]+)")
_DEEZER_PATH = re.compile(
    r"^/(?:[a-z]{2}/)?(track|album|playlist|artist)/([0-9]+)"
)
_SOUNDCLOUD_SET = re.compile(r"^/([^/?#]+)/sets/([^/?#]+)")
_SOUNDCLOUD_TRACK = re.compile(r"^/([^/?#]+)/([^/?#]+)")


def parse_music_url(raw_url: str) -> MusicLink:
    """Parse ``raw_url`` into a :class:`MusicLink`.

    Raises :class:`UnsupportedMusicLinkError` when the link does not point at a
    song, album, playlist or artist on a supported provider.
    """
    url = (raw_url or "").strip()
    if not url:
        raise UnsupportedMusicLinkError("A music link is required.")

    uri_match = _SPOTIFY_URI.match(url)
    if uri_match:
        kind, item_id = uri_match.groups()
        return MusicLink(
            provider=Provider.SPOTIFY,
            item_type=_SPOTIFY_TYPES[kind],
            provider_item_id=item_id,
            url=f"https://open.spotify.com/{kind}/{item_id}",
        )

    if "://" not in url:
        url = f"https://{url}"

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UnsupportedMusicLinkError("Only http(s) music links are supported.")

    host = parsed.netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"

    if host in {"open.spotify.com", "play.spotify.com", "spotify.link"}:
        return _parse_spotify(host, path, url)
    if host in {"music.apple.com", "embed.music.apple.com", "itunes.apple.com"}:
        return _parse_apple(path, parsed.query, url)
    if host in {"music.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}:
        return _parse_youtube(host, path, parsed.query, url)
    if host in {"soundcloud.com", "m.soundcloud.com", "on.soundcloud.com"}:
        return _parse_soundcloud(path, url)
    if host in {"tidal.com", "listen.tidal.com", "embed.tidal.com"}:
        return _parse_simple(_TIDAL_PATH, Provider.TIDAL, path, url)
    if host in {"deezer.com", "link.deezer.com"}:
        return _parse_simple(_DEEZER_PATH, Provider.DEEZER, path, url)
    if host.endswith("bandcamp.com"):
        return _parse_bandcamp(host, path, url)

    raise UnsupportedMusicLinkError(
        "Link must be a song, album or playlist from Spotify, Apple Music, "
        "YouTube Music, SoundCloud, TIDAL, Deezer or Bandcamp."
    )


def _parse_spotify(host: str, path: str, url: str) -> MusicLink:
    if host == "spotify.link":
        # Short share link: we cannot resolve the target offline, but it is a
        # valid Spotify item, so keep the link itself as the identifier.
        return MusicLink(Provider.SPOTIFY, ItemType.TRACK, path.strip("/"), url)

    match = _SPOTIFY_PATH.match(path)
    if not match:
        raise UnsupportedMusicLinkError(
            "Spotify link must point at a track, album, playlist or artist."
        )
    kind, item_id = match.groups()
    return MusicLink(
        provider=Provider.SPOTIFY,
        item_type=_SPOTIFY_TYPES[kind],
        provider_item_id=item_id,
        url=f"https://open.spotify.com/{kind}/{item_id}",
    )


def _parse_apple(path: str, query: str, url: str) -> MusicLink:
    match = _APPLE_PATH.match(path)
    if not match:
        raise UnsupportedMusicLinkError(
            "Apple Music link must point at a song, album or playlist."
        )
    kind, _slug, item_id = match.groups()
    song_id = parse_qs(query).get("i", [None])[0]

    if kind == "playlist":
        item_type = ItemType.PLAYLIST
    elif kind == "artist":
        item_type = ItemType.ARTIST
    elif kind in {"song", "music-video"} or song_id:
        item_type = ItemType.TRACK
    else:
        item_type = ItemType.ALBUM

    return MusicLink(
        provider=Provider.APPLE_MUSIC,
        item_type=item_type,
        provider_item_id=song_id or item_id,
        url=url,
    )


def _parse_youtube(host: str, path: str, query: str, url: str) -> MusicLink:
    params = parse_qs(query)
    if host == "youtu.be":
        video_id = path.strip("/").split("/")[0]
        if not video_id:
            raise UnsupportedMusicLinkError("YouTube link is missing a video id.")
        return MusicLink(
            Provider.YOUTUBE_MUSIC,
            ItemType.TRACK,
            video_id,
            f"https://music.youtube.com/watch?v={video_id}",
        )

    if path.startswith("/watch") and params.get("v"):
        video_id = params["v"][0]
        return MusicLink(
            Provider.YOUTUBE_MUSIC,
            ItemType.TRACK,
            video_id,
            f"https://music.youtube.com/watch?v={video_id}",
        )

    if path.startswith("/playlist") and params.get("list"):
        list_id = params["list"][0]
        return MusicLink(
            Provider.YOUTUBE_MUSIC,
            ItemType.PLAYLIST,
            list_id,
            f"https://music.youtube.com/playlist?list={list_id}",
        )

    raise UnsupportedMusicLinkError(
        "YouTube link must point at a video or playlist."
    )


def _parse_soundcloud(path: str, url: str) -> MusicLink:
    set_match = _SOUNDCLOUD_SET.match(path)
    if set_match:
        user, slug = set_match.groups()
        return MusicLink(Provider.SOUNDCLOUD, ItemType.PLAYLIST, f"{user}/sets/{slug}", url)

    track_match = _SOUNDCLOUD_TRACK.match(path)
    if track_match:
        user, slug = track_match.groups()
        return MusicLink(Provider.SOUNDCLOUD, ItemType.TRACK, f"{user}/{slug}", url)

    raise UnsupportedMusicLinkError("SoundCloud link must point at a track or set.")


def _parse_bandcamp(host: str, path: str, url: str) -> MusicLink:
    match = _BANDCAMP_PATH.match(path)
    if not match:
        raise UnsupportedMusicLinkError("Bandcamp link must point at a track or album.")
    kind, slug = match.groups()
    item_type = ItemType.TRACK if kind == "track" else ItemType.ALBUM
    return MusicLink(Provider.BANDCAMP, item_type, f"{host}/{kind}/{slug}", url)


def _parse_simple(
    pattern: re.Pattern[str], provider: Provider, path: str, url: str
) -> MusicLink:
    match = pattern.match(path)
    if not match:
        raise UnsupportedMusicLinkError(
            f"{PROVIDER_DISPLAY_NAMES[provider]} link must point at a track, "
            "album or playlist."
        )
    kind, item_id = match.groups()
    return MusicLink(provider, ItemType(kind), item_id, url)


# ── Metadata ──────────────────────────────────────────────────────────────────

_OEMBED_ENDPOINTS = {
    Provider.SPOTIFY: "https://open.spotify.com/oembed",
    Provider.SOUNDCLOUD: "https://soundcloud.com/oembed",
    Provider.YOUTUBE_MUSIC: "https://www.youtube.com/oembed",
    Provider.DEEZER: "https://api.deezer.com/oembed",
    Provider.BANDCAMP: "https://bandcamp.com/api/mobile/25/oembed",
}

_OG_TAG = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:(title|image|audio)["\'][^>]*'
    r'content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_TAG_REVERSED = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']og:'
    r'(title|image|audio)["\']',
    re.IGNORECASE,
)

# Providers whose pages we scrape for OpenGraph tags because they expose no
# public oEmbed endpoint.
_OG_SCRAPE_PROVIDERS = {Provider.APPLE_MUSIC, Provider.TIDAL}

_MAX_HTML_BYTES = 200_000


def fetch_metadata(link: MusicLink) -> MusicMetadata:
    """Look up title/artwork for ``link``. Never raises — worst case is empty."""
    if not settings.enable_link_metadata:
        return MusicMetadata()

    try:
        if link.provider in _OEMBED_ENDPOINTS:
            return _fetch_oembed(link)
        if link.provider in _OG_SCRAPE_PROVIDERS:
            return _fetch_opengraph(link)
    except Exception:  # noqa: BLE001 - enrichment must never break posting
        return MusicMetadata()
    return MusicMetadata()


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=settings.link_metadata_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "SetlistBot/1.0 (+https://github.com/kalvoada/Setlist)"},
    )


def _fetch_oembed(link: MusicLink) -> MusicMetadata:
    endpoint = _OEMBED_ENDPOINTS[link.provider]
    with _client() as client:
        response = client.get(endpoint, params={"url": link.url, "format": "json"})
        response.raise_for_status()
        payload = response.json()

    title = payload.get("title")
    artist = payload.get("author_name")
    if title and artist and title.lower().startswith(f"{artist.lower()} - "):
        title = title[len(artist) + 3 :]

    return MusicMetadata(
        title=title,
        artist_name=artist,
        artwork_url=payload.get("thumbnail_url"),
    )


def _fetch_opengraph(link: MusicLink) -> MusicMetadata:
    with _client() as client:
        response = client.get(link.url)
        response.raise_for_status()
        html = response.text[:_MAX_HTML_BYTES]

    tags: dict[str, str] = {}
    for key, value in _OG_TAG.findall(html):
        tags.setdefault(key.lower(), value)
    for value, key in _OG_TAG_REVERSED.findall(html):
        tags.setdefault(key.lower(), value)

    title = tags.get("title")
    artist = None
    # Apple Music renders "Song by Artist on Apple Music".
    if title:
        title = re.sub(r"\s+on Apple Music\s*$", "", title).strip()
        match = re.match(r"^(?P<title>.+?)\s+by\s+(?P<artist>.+)$", title)
        if match:
            title = match.group("title").strip()
            artist = match.group("artist").strip()

    return MusicMetadata(
        title=title,
        artist_name=artist,
        artwork_url=tags.get("image"),
        preview_url=tags.get("audio"),
    )


def fallback_title(link: MusicLink) -> str:
    """A human-readable title derived from the URL when lookup fails."""
    slug = ""
    path_parts = [part for part in urlparse(link.url).path.split("/") if part]

    if link.provider == Provider.APPLE_MUSIC and len(path_parts) >= 3:
        slug = path_parts[2]
    elif link.provider == Provider.SOUNDCLOUD and path_parts:
        slug = path_parts[-1]
    elif link.provider == Provider.BANDCAMP and path_parts:
        slug = path_parts[-1]

    slug = re.sub(r"[-_]+", " ", slug).strip()
    if slug and not re.fullmatch(r"[0-9]+", slug):
        return slug.title()[:300]

    return f"{PROVIDER_DISPLAY_NAMES[link.provider]} {link.item_type.value}"
