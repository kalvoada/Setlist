"""
Parsing and enrichment of streaming-service links.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
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
    # Tracks only; tells a remaster from a live take or an edit when matching.
    duration_ms: Optional[int] = None


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
    """
    Parse ``raw_url`` into a :class:`MusicLink`.

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

_OG_SCRAPE_PROVIDERS = {Provider.APPLE_MUSIC, Provider.TIDAL, Provider.BANDCAMP}

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

    return parse_opengraph(response.text[:_MAX_HTML_BYTES])


def parse_opengraph(html: str) -> MusicMetadata:
    """Pull title/artist/artwork out of a page's OpenGraph tags."""
    tags: dict[str, str] = {}
    for key, value in _OG_TAG.findall(html):
        tags.setdefault(key.lower(), value)
    for value, key in _OG_TAG_REVERSED.findall(html):
        tags.setdefault(key.lower(), value)

    title = tags.get("title")
    artist = None
    if title:
        title = re.sub(r"\s+on Apple Music\s*$", "", title).strip()
        match = re.match(r"^(?P<title>.+?),?\s+by\s+(?P<artist>.+)$", title)
        if match:
            title = match.group("title").strip().rstrip(",")
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


# ── Cross-provider links ──────────────────────────────────────────────────────
#
# The item's own service describes it (title, artist, length), then the other
# service's catalogue is searched for it. A candidate is only accepted when its
# own metadata agrees, so a doubtful match reads as "not available" instead of
# opening the wrong song. Apple's free iTunes API has no ISRC lookup, so title,
# artist and length are what both directions can compare.

_ITUNES_API = "https://itunes.apple.com"
_SPOTIFY_API = "https://api.spotify.com/v1"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Remasters and re-releases differ by a second or two; edits and live takes by more.
_DURATION_TOLERANCE_MS = 3000

# Playlists and artist pages are specific to one service.
_TRANSLATABLE_TYPES = {ItemType.TRACK, ItemType.ALBUM}

_spotify_token: Optional[tuple[str, float]] = None  # (token, expires at)


class LinkResolutionError(RuntimeError):
    """The lookup failed for now (network, timeout, rate limit); try again later."""


def can_translate(source: str, target: str, item_type: str) -> bool:
    """Whether an item on ``source`` can have a reliable equivalent on ``target``."""
    try:
        providers = {Provider(source), Provider(target)}
        kind = ItemType(item_type)
    except ValueError:
        return False
    return kind in _TRANSLATABLE_TYPES and providers <= _CATALOGUES.keys()


def resolve_links(url: str) -> dict[str, str]:
    """
    Verified links to the same song or album on the other services, keyed by
    provider value. An empty dict means none were found.

    Raises :class:`LinkResolutionError` when the answer is unknown for now.
    """
    if not settings.enable_link_metadata:
        raise LinkResolutionError("Link lookups are disabled (ENABLE_LINK_METADATA).")

    try:
        link = parse_music_url(url)
    except UnsupportedMusicLinkError:
        return {}
    if link.provider not in _CATALOGUES or link.item_type not in _TRANSLATABLE_TYPES:
        return {}

    try:
        with _client() as client:
            lookup, _ = _CATALOGUES[link.provider]
            source = lookup(client, link)
            if source is None or not source.title or not source.artist_name:
                return {}

            links: dict[str, str] = {}
            for provider, (_, search) in _CATALOGUES.items():
                if provider is link.provider:
                    continue
                candidates = search(client, link.item_type, source)
                match = best_match(source, link.item_type, candidates)
                if match is not None:
                    links[provider.value] = match.url
            return links
    except httpx.HTTPStatusError as exc:
        raise LinkResolutionError(
            f"{exc.request.url.host} answered {exc.response.status_code}: "
            f"{exc.response.text[:300]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise LinkResolutionError(f"Music service unreachable: {exc!r}") from exc
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise LinkResolutionError(f"Unexpected answer: {exc!r}") from exc


def best_match(
    source: MusicMetadata,
    kind: ItemType,
    candidates: list[tuple[MusicLink, MusicMetadata]],
) -> Optional[MusicLink]:
    """The candidate that is the same music as ``source``, if any."""
    matches = [
        (link, metadata)
        for link, metadata in candidates
        if link.item_type is kind and _same_music(source, metadata)
    ]
    # The same recording is often on an album and a compilation; both are fine,
    # the closest length wins.
    length = source.duration_ms or 0
    matches.sort(key=lambda match: abs((match[1].duration_ms or 0) - length))
    return matches[0][0] if matches else None


def _get_json(client: httpx.Client, url: str, **kwargs) -> Any:
    """GET ``url``; None when the service doesn't know it (400/404)."""
    response = client.get(url, **kwargs)
    if response.status_code in {400, 404}:
        return None
    response.raise_for_status()
    return response.json()


# Apple Music, through the public iTunes Search API.


def _itunes_entry(item: dict[str, Any]) -> tuple[MusicLink, MusicMetadata]:
    is_track = item.get("wrapperType") == "track"
    link = parse_music_url(item["trackViewUrl" if is_track else "collectionViewUrl"])
    return link, MusicMetadata(
        title=item.get("trackName" if is_track else "collectionName"),
        artist_name=item.get("artistName"),
        duration_ms=item.get("trackTimeMillis") if is_track else None,
    )


def _itunes_lookup(client: httpx.Client, link: MusicLink) -> Optional[MusicMetadata]:
    storefront = re.match(r"^/([a-z]{2})/", urlparse(link.url).path)
    payload = _get_json(
        client,
        f"{_ITUNES_API}/lookup",
        params={
            "id": link.provider_item_id,
            "country": storefront.group(1) if storefront else "us",
        },
    )
    results = (payload or {}).get("results") or []
    return _itunes_entry(results[0])[1] if results else None


def _itunes_search(
    client: httpx.Client, kind: ItemType, source: MusicMetadata
) -> list[tuple[MusicLink, MusicMetadata]]:
    payload = _get_json(
        client,
        f"{_ITUNES_API}/search",
        params={
            "term": f"{_primary_artist(source)} {_plain_title(source.title)}",
            "entity": "song" if kind is ItemType.TRACK else "album",
            "country": "us",
            "limit": 25,
        },
    )
    return [_itunes_entry(item) for item in (payload or {}).get("results") or []]


# Spotify, through the Web API with the app's own (client credentials) token.


def _spotify_headers(client: httpx.Client) -> dict[str, str]:
    global _spotify_token
    if not (settings.spotify_client_id and settings.spotify_client_secret):
        raise LinkResolutionError(
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to match music on Spotify."
        )
    if _spotify_token is None or _spotify_token[1] <= time.monotonic():
        response = client.post(
            _SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
        )
        response.raise_for_status()
        payload = response.json()
        # Renewed a minute early so it never expires mid-lookup.
        _spotify_token = (
            payload["access_token"],
            time.monotonic() + payload["expires_in"] - 60,
        )
    return {"Authorization": f"Bearer {_spotify_token[0]}"}


def _spotify_entry(item: dict[str, Any]) -> tuple[MusicLink, MusicMetadata]:
    return parse_music_url(item["external_urls"]["spotify"]), MusicMetadata(
        title=item.get("name"),
        artist_name=", ".join(artist["name"] for artist in item.get("artists") or []),
        duration_ms=item.get("duration_ms"),
    )


def _spotify_lookup(client: httpx.Client, link: MusicLink) -> Optional[MusicMetadata]:
    kind = "tracks" if link.item_type is ItemType.TRACK else "albums"
    item = _get_json(
        client,
        f"{_SPOTIFY_API}/{kind}/{link.provider_item_id}",
        headers=_spotify_headers(client),
    )
    return _spotify_entry(item)[1] if item else None


def _spotify_search(
    client: httpx.Client, kind: ItemType, source: MusicMetadata
) -> list[tuple[MusicLink, MusicMetadata]]:
    field = "track" if kind is ItemType.TRACK else "album"
    title = _plain_title(source.title).replace('"', "")
    artist = _primary_artist(source).replace('"', "")
    payload = _get_json(
        client,
        f"{_SPOTIFY_API}/search",
        params={"q": f'{field}:"{title}" artist:"{artist}"', "type": field, "limit": 10},
        headers=_spotify_headers(client),
    )
    items = ((payload or {}).get(f"{field}s") or {}).get("items") or []
    return [_spotify_entry(item) for item in items if item]


# provider: (describe an item, search for one like it)
_CATALOGUES = {
    Provider.SPOTIFY: (_spotify_lookup, _spotify_search),
    Provider.APPLE_MUSIC: (_itunes_lookup, _itunes_search),
}


# ── Matching ──────────────────────────────────────────────────────────────────

_FEATURING = re.compile(
    r"[(\[]\s*(?:feat|ft|featuring|with)\b[^)\]]*[)\]]|\s-\s(?:feat|ft)\b.*$",
    re.IGNORECASE,
)
# A remaster is the same recording. Spotify tags it in the title ("Come Together
# - Remastered 2009"); Apple Music usually doesn't.
_REMASTER = re.compile(
    r"\s(?:-\s|[(\[])(?:\d{4}\s)?(?:digital\s)?remaster(?:ed)?(?:\s\d{4})?"
    r"(?:\sversion)?[)\]]?$",
    re.IGNORECASE,
)
_ARTIST_SEPARATORS = re.compile(
    r"[,&;/+]|\s(?:feat\.?|ft\.?|featuring|with|and|x)\s", re.IGNORECASE
)


def _plain_title(title: Optional[str]) -> str:
    """The title without "feat." credits and remaster tags."""
    return _REMASTER.sub("", _FEATURING.sub("", title or "").strip())


def _primary_artist(metadata: MusicMetadata) -> str:
    return _ARTIST_SEPARATORS.split(metadata.artist_name or "")[0].strip()


def _normalize(text: str) -> str:
    """Case, accents, punctuation, "feat." credits and remaster tags don't make a
    different song."""
    text = unicodedata.normalize("NFKD", _plain_title(text)).casefold()
    return "".join(char for char in text if char.isalnum())


def _artists(name: Optional[str]) -> set[str]:
    return {
        artist
        for artist in map(_normalize, _ARTIST_SEPARATORS.split(name or ""))
        if artist
    }


def _same_music(a: MusicMetadata, b: MusicMetadata) -> bool:
    """Same title, an artist in common and, when both are known, the same length."""
    title = _normalize(a.title or "")
    if not title or title != _normalize(b.title or ""):
        return False
    if not _artists(a.artist_name) & _artists(b.artist_name):
        return False
    if a.duration_ms and b.duration_ms:
        return abs(a.duration_ms - b.duration_ms) <= _DURATION_TOLERANCE_MS
    return True
