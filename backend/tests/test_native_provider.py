"""Opening shared music on the listener's own streaming service."""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from conftest import SPOTIFY_TRACK

from src import music
from src.database import models
from src.database.database import SessionLocal
from src.music import ItemType, MusicMetadata, parse_music_url

BANDCAMP_TRACK = "https://artist.bandcamp.com/track/some-song"
SOUNDCLOUD_TRACK = "https://soundcloud.com/artist/some-song"
SPOTIFY_PLAYLIST = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
YOUTUBE_PLAYLIST = (
    "https://music.youtube.com/playlist?list=PL4fGSI1pDJn6puJdseH2Rt9sMvt9E2M4i"
)
BANDCAMP_PLAYER = "https://bandcamp.com/EmbeddedPlayer/v=2/track=2436476419/size=large/"

SERVICES = ("spotify", "apple_music", "youtube_music")


# ── A small catalogue, the way each service lists it ──────────────────────────
#
# Titles and lengths follow each service's conventions (Spotify tags remasters,
# Apple Music doesn't, YouTube Music puts them in brackets and rounds lengths to
# the second). Apple and YouTube ids are illustrative.


@dataclass(frozen=True)
class Release:
    id: str
    title: str
    artist: str
    ms: int


@dataclass(frozen=True)
class Song:
    name: str  # what a search for it contains
    releases: dict[str, Release]
    # Other results the same search returns: covers, live takes, other mixes.
    decoys: dict[str, list[Release]]


SONGS = [
    Song(
        "come together",
        {
            "spotify": Release(
                "2EqlS6tkEnglzr7tkKAAYD",
                "Come Together - Remastered 2009",
                "The Beatles",
                259_946,
            ),
            "apple_music": Release("1441164430", "Come Together", "The Beatles", 259_947),
            "youtube_music": Release(
                "Hj6rYAOtV8E", "Come Together (Remastered 2009)", "The Beatles", 260_000
            ),
        },
        {
            "spotify": [
                Release("0mix2019", "Come Together - 2019 Mix", "The Beatles", 259_000),
                Release("0aerosmith", "Come Together", "Aerosmith", 225_000),
            ],
            "apple_music": [
                Release("1111", "Come Together (Live)", "The Beatles", 270_000),
                Release("1112", "Come Together", "Aerosmith", 225_000),
            ],
            "youtube_music": [
                Release("ArcticMonk1", "Come Together", "Arctic Monkeys", 211_000),
            ],
        },
    ),
    Song(
        "bohemian rhapsody",
        {
            "spotify": Release(
                "7tFiyTwD0nx5a1eklYtX2J",
                "Bohemian Rhapsody - Remastered 2011",
                "Queen",
                354_320,
            ),
            "apple_music": Release("1440806768", "Bohemian Rhapsody", "Queen", 354_947),
            "youtube_music": Release(
                "fJ9rUzIMcZQ", "Bohemian Rhapsody (Remastered 2011)", "Queen", 355_000
            ),
        },
        {
            "spotify": [
                Release("0liveaid", "Bohemian Rhapsody - Live Aid", "Queen", 148_000),
                Release("0panic", "Bohemian Rhapsody", "Panic! At The Disco", 367_000),
            ],
            "apple_music": [
                Release("2221", "Bohemian Rhapsody", "Panic! At the Disco", 367_000),
            ],
            "youtube_music": [
                Release("MuppetsBoh1", "Bohemian Rhapsody", "The Muppets", 290_000),
            ],
        },
    ),
    Song(
        "billie jean",
        {
            "spotify": Release(
                "5ChkMS8OtdzJeqyybCc9R5", "Billie Jean", "Michael Jackson", 293_826
            ),
            "apple_music": Release(
                "269573364", "Billie Jean", "Michael Jackson", 294_227
            ),
            "youtube_music": Release(
                "Zi_XLOBDo_Y", "Billie Jean", "Michael Jackson", 294_000
            ),
        },
        {
            "spotify": [
                Release("0civilwars", "Billie Jean", "The Civil Wars", 282_000),
                Release(
                    "0single", "Billie Jean - Single Version", "Michael Jackson", 280_000
                ),
            ],
            "apple_music": [
                Release("3331", "Billie Jean (Karaoke Version)", "Party Band", 294_000),
            ],
            "youtube_music": [
                Release("CivilWarsBJ", "Billie Jean", "The Civil Wars", 282_000),
            ],
        },
    ),
    Song(
        "smells like teen spirit",
        {
            "spotify": Release(
                "5ghIJDpPoe3CfHMGu71E6T", "Smells Like Teen Spirit", "Nirvana", 301_920
            ),
            "apple_music": Release(
                "1440783625", "Smells Like Teen Spirit", "Nirvana", 301_920
            ),
            "youtube_music": Release(
                "A5W0p-Ec4Mg", "Smells Like Teen Spirit", "Nirvana", 302_000
            ),
        },
        {
            "spotify": [
                Release("0toriamos", "Smells Like Teen Spirit", "Tori Amos", 293_000),
                Release(
                    "0reading",
                    "Smells Like Teen Spirit - Live at Reading",
                    "Nirvana",
                    290_000,
                ),
            ],
            "apple_music": [
                Release("4441", "Smells Like Teen Spirit", "Tori Amos", 293_000),
            ],
            "youtube_music": [
                Release("PatSmithSLT", "Smells Like Teen Spirit", "Patti Smith", 290_000),
            ],
        },
    ),
    Song(
        "blinding lights",
        {
            "spotify": Release(
                "0VjIjW4GlUZAMYd2vXMi3b", "Blinding Lights", "The Weeknd", 200_040
            ),
            "apple_music": Release(
                "1499378615", "Blinding Lights", "The Weeknd", 200_040
            ),
            "youtube_music": Release(
                "J7p4bzqLvCw", "Blinding Lights", "The Weeknd", 200_000
            ),
        },
        {
            "spotify": [
                Release(
                    "0remix",
                    "Blinding Lights (with ROSALÍA) - Remix",
                    "The Weeknd, ROSALÍA",
                    202_000,
                ),
            ],
            "apple_music": [
                Release(
                    "5551", "Blinding Lights (Chromatics Remix)", "The Weeknd", 290_000
                ),
            ],
            "youtube_music": [
                Release("LoiCoverBL1", "Blinding Lights", "Loi", 190_000),
            ],
        },
    ),
]


def source_url(service: str, release: Release) -> str:
    """How someone would share ``release``."""
    return {
        "spotify": f"https://open.spotify.com/track/{release.id}",
        "apple_music": f"https://music.apple.com/us/album/song/1440000000?i={release.id}",
        "youtube_music": f"https://music.youtube.com/watch?v={release.id}",
    }[service]


def resolved_url(service: str, release: Release) -> str:
    """The link Setlist should open ``release`` with."""
    if service == "apple_music":
        return f"https://music.apple.com/us/album/song/1440000000?i={release.id}&uo=4"
    return source_url(service, release)


# ── What the services answer ──────────────────────────────────────────────────


def spotify_track(release: Release) -> dict:
    return {
        "album": {"album_type": "album", "name": "Some Album"},
        "artists": [
            {"name": name, "type": "artist"} for name in release.artist.split(", ")
        ],
        "duration_ms": release.ms,
        "external_urls": {"spotify": f"https://open.spotify.com/track/{release.id}"},
        "id": release.id,
        "name": release.title,
        "type": "track",
    }


def itunes_song(release: Release) -> dict:
    url = f"https://music.apple.com/us/album/song/1440000000?i={release.id}&uo=4"
    return {
        "wrapperType": "track",
        "kind": "song",
        "artistName": release.artist,
        "collectionName": "Some Album",
        "trackName": release.title,
        "trackId": int(release.id),
        "collectionViewUrl": url,
        "trackViewUrl": url,
        "trackTimeMillis": release.ms,
    }


def youtube_song(release: Release) -> dict:
    return {
        "category": "Songs",
        "resultType": "song",
        "videoId": release.id,
        "title": release.title,
        "artists": [{"name": release.artist, "id": "UC123"}],
        "album": {"name": "Some Album", "id": "MPREb_1"},
        "duration": f"{release.ms // 60_000}:{release.ms // 1000 % 60:02}",
        "duration_seconds": release.ms // 1000,
        "isExplicit": False,
    }


def youtube_details(release: Release, video_type: str = "MUSIC_VIDEO_TYPE_ATV") -> dict:
    return {
        "videoDetails": {
            "videoId": release.id,
            "title": release.title,
            "lengthSeconds": str(release.ms // 1000),
            "author": release.artist,
            "musicVideoType": video_type,
        }
    }


class FakeCatalogues:
    """
    Answers like Spotify's Web API, Apple's iTunes Search API and ytmusicapi,
    from SONGS. ``break_route`` makes one of them fail.
    """

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.youtube_calls: list[tuple] = []
        self.broken: dict[str, object] = {}
        self.videos: dict[str, dict] = {}
        self.overrides: dict[str, object] = {}

    # Test controls.

    def break_route(self, route: str, failure) -> None:
        """``failure``: an exception, ``(status, json)`` or a text body."""
        self.broken[route] = failure

    def fix(self) -> None:
        self.broken.clear()

    def calls(self, route: str) -> list[httpx.Request]:
        return [r for r in self.requests if (r.url.host + r.url.path).startswith(route)]

    # Lookups in the catalogue.

    @staticmethod
    def song_for(query: str) -> Song | None:
        return next((song for song in SONGS if song.name in query.casefold()), None)

    @staticmethod
    def release(service: str, release_id: str) -> Release | None:
        for song in SONGS:
            for release in [song.releases[service], *song.decoys[service]]:
                if release.id == release_id:
                    return release
        return None

    def results(self, service: str, query: str) -> list[Release]:
        song = self.song_for(query)
        # Decoys first: the right one isn't always the top hit.
        return [*song.decoys[service], song.releases[service]] if song else []

    # httpx: Spotify and iTunes.

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = request.url.host + request.url.path
        for broken, failure in self.broken.items():
            if route.startswith(broken):
                if isinstance(failure, Exception):
                    raise failure
                if isinstance(failure, str):
                    return httpx.Response(200, text=failure)
                return httpx.Response(failure[0], json=failure[1])
        if route in self.overrides:
            return httpx.Response(200, json=self.overrides[route])

        params = request.url.params
        if route == "accounts.spotify.com/api/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "BQD-app-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if route.startswith("api.spotify.com/v1/tracks/"):
            release = self.release("spotify", route.rsplit("/", 1)[1])
            if release is None:
                return httpx.Response(404, json={"error": {"status": 404}})
            return httpx.Response(200, json=spotify_track(release))
        if route == "api.spotify.com/v1/search":
            items = [spotify_track(r) for r in self.results("spotify", params["q"])]
            return httpx.Response(
                200, json={"tracks": {"items": items, "total": len(items)}}
            )
        if route == "itunes.apple.com/lookup":
            release = self.release("apple_music", params["id"])
            found = [itunes_song(release)] if release else []
            return httpx.Response(200, json={"resultCount": len(found), "results": found})
        if route == "itunes.apple.com/search":
            found = [itunes_song(r) for r in self.results("apple_music", params["term"])]
            return httpx.Response(200, json={"resultCount": len(found), "results": found})
        return httpx.Response(404, json={"error": {"status": 404}})

    # ytmusicapi.

    def _youtube(self, call: tuple):
        self.youtube_calls.append(call)
        if "youtube" in self.broken:
            raise self.broken["youtube"]

    def search(
        self, query: str, filter: str | None = None, limit: int = 20
    ) -> list[dict]:
        self._youtube(("search", query, filter))
        if filter == "albums":
            return self.overrides.get("youtube albums", [])
        return [youtube_song(r) for r in self.results("youtube_music", query)]

    def get_song(self, video_id: str) -> dict:
        self._youtube(("get_song", video_id))
        if video_id in self.videos:
            return self.videos[video_id]
        release = self.release("youtube_music", video_id)
        return youtube_details(release) if release else {"playabilityStatus": {}}


@pytest.fixture
def catalogues(monkeypatch) -> FakeCatalogues:
    fake = FakeCatalogues()
    monkeypatch.setattr(music.settings, "enable_link_metadata", True)
    monkeypatch.setattr(music.settings, "spotify_client_id", "client-id")
    monkeypatch.setattr(music.settings, "spotify_client_secret", "client-secret")
    monkeypatch.setattr(music, "_spotify_token", None)
    monkeypatch.setattr(
        music, "_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handle))
    )
    monkeypatch.setattr(music, "_ytmusic", lambda: fake)
    return fake


def choose(client, user: dict, provider: str) -> dict:
    response = client.patch(
        "/users/me", json={"native_provider": provider}, headers=user["headers"]
    )
    assert response.status_code == 200, response.text
    return response.json()


def native_link(client, user: dict, post: dict):
    return client.get(
        f"/music/{post['music']['id']}/native-link", headers=user["headers"]
    )


def feed_music(client, user: dict, post: dict) -> dict:
    return client.get(f"/posts/{post['id']}", headers=user["headers"]).json()["music"]


def feed_native(client, user: dict, post: dict) -> dict | None:
    return feed_music(client, user, post)["native"]


# ── Every direction, for five well-known songs ───────────────────────────────


@pytest.mark.parametrize(
    ("song", "source", "target"),
    [
        pytest.param(song, source, target, id=f"{song.name}: {source} -> {target}")
        for song in SONGS
        for source, target in itertools.permutations(SERVICES, 2)
    ],
)
def test_song_opens_on_every_other_service(
    client, alice, make_post, catalogues, song, source, target
):
    post = make_post(alice["headers"], url=source_url(source, song.releases[source]))
    choose(client, alice, target)

    response = native_link(client, alice, post)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "resolved", response.json()
    assert response.json()["url"] == resolved_url(target, song.releases[target])
    assert response.json()["embed_url"] == music.embed_url(response.json()["url"])


def test_a_youtube_music_video_opens_on_spotify(client, alice, make_post, catalogues):
    # The official video: YouTube's title and channel, and a longer running time.
    catalogues.videos["hTWKbfoikeg"] = youtube_details(
        Release(
            "hTWKbfoikeg",
            "Nirvana - Smells Like Teen Spirit (Official Music Video)",
            "NirvanaVEVO",
            279_000,
        ),
        video_type="MUSIC_VIDEO_TYPE_OMV",
    )
    post = make_post(alice["headers"], url="https://www.youtube.com/watch?v=hTWKbfoikeg")
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert (
        response.json()["url"] == "https://open.spotify.com/track/5ghIJDpPoe3CfHMGu71E6T"
    )


# ── How the services are asked ────────────────────────────────────────────────


def test_apple_music_to_spotify_asks_the_way_each_service_expects(
    client, alice, make_post, catalogues
):
    come_together = SONGS[0].releases["apple_music"]
    post = make_post(alice["headers"], url=source_url("apple_music", come_together))
    choose(client, alice, "spotify")

    native_link(client, alice, post)

    lookup = catalogues.calls("itunes.apple.com/lookup")[0]
    assert lookup.url.params["id"] == "1441164430"
    assert lookup.url.params["country"] == "us"
    search = catalogues.calls("api.spotify.com/v1/search")[0]
    assert search.url.params["q"] == "Come Together The Beatles"
    assert search.url.params["type"] == "track"
    assert search.headers["Authorization"] == "Bearer BQD-app-token"
    token = catalogues.calls("accounts.spotify.com/api/token")[0]
    assert token.headers["Authorization"].startswith("Basic ")
    assert parse_qs(token.content.decode()) == {"grant_type": ["client_credentials"]}


def test_spotify_to_youtube_music_searches_songs(client, alice, make_post, catalogues):
    bohemian = SONGS[1].releases["spotify"]
    post = make_post(alice["headers"], url=source_url("spotify", bohemian))
    choose(client, alice, "youtube_music")

    native_link(client, alice, post)

    assert ("search", "Queen Bohemian Rhapsody", "songs") in catalogues.youtube_calls


def test_album_on_spotify_opens_on_youtube_music(client, alice, make_post, catalogues):
    catalogues.overrides["api.spotify.com/v1/albums/0ETFjACtuP2ADo6LFhL6HN"] = {
        "album_type": "album",
        "artists": [{"name": "The Beatles"}],
        "external_urls": {
            "spotify": "https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN"
        },
        "name": "Abbey Road (Remastered)",
    }
    catalogues.overrides["youtube albums"] = [
        {
            "resultType": "album",
            "title": "Abbey Road (Super Deluxe Edition)",
            "artists": [{"name": "The Beatles"}],
            "playlistId": "OLAK5uy_deluxe",
        },
        {
            "resultType": "album",
            "title": "Abbey Road (Remastered)",
            "artists": [{"name": "The Beatles"}],
            "playlistId": "OLAK5uy_abbeyroad",
        },
    ]
    post = make_post(
        alice["headers"], url="https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN"
    )
    choose(client, alice, "youtube_music")

    response = native_link(client, alice, post)

    assert (
        response.json()["url"]
        == "https://music.youtube.com/playlist?list=OLAK5uy_abbeyroad"
    )
    # YouTube Music has no player to embed; the app draws its own card.
    assert response.json()["embed_url"] is None


# ── What posts say ────────────────────────────────────────────────────────────


def test_native_provider_is_saved_on_the_account(client, alice):
    me = client.get("/users/me", headers=alice["headers"]).json()
    assert me["native_provider"] is None

    assert choose(client, alice, "youtube_music")["native_provider"] == "youtube_music"
    assert (
        client.get("/users/me", headers=alice["headers"]).json()["native_provider"]
        == "youtube_music"
    )
    # It is a private setting, not part of the public profile.
    assert "native_provider" not in client.get(f"/users/{alice['user']['id']}").json()


def test_native_provider_can_be_cleared(client, alice):
    choose(client, alice, "spotify")
    assert choose(client, alice, "")["native_provider"] is None


@pytest.mark.parametrize("provider", ["napster", "bandcamp", "soundcloud", "tidal"])
def test_only_services_music_can_be_matched_into_can_be_chosen(client, alice, provider):
    response = client.patch(
        "/users/me", json={"native_provider": provider}, headers=alice["headers"]
    )
    assert response.status_code == 422
    assert "Unknown music service" in response.text


def test_editing_the_profile_keeps_the_native_provider(client, alice):
    choose(client, alice, "apple_music")
    response = client.patch("/users/me", json={"bio": "hi"}, headers=alice["headers"])
    assert response.json()["native_provider"] == "apple_music"


def test_without_a_native_provider_posts_show_the_original_player(
    client, alice, make_post
):
    post = make_post(alice["headers"])

    assert post["music"]["native"] is None
    assert post["music"]["embed_url"] == (
        "https://open.spotify.com/embed/track/4cOdK2wGLETKBW3PvgPWqT"
    )
    assert client.get("/posts/").json()["items"][0]["music"]["native"] is None


def test_each_viewer_sees_their_own_service(client, alice, bob, make_post):
    make_post(alice["headers"])
    choose(client, alice, "apple_music")
    choose(client, bob, "spotify")

    feed = client.get("/posts/", headers=alice["headers"]).json()
    assert feed["items"][0]["music"]["native"] == {
        "status": "pending",
        "provider": "apple_music",
        "provider_name": "Apple Music",
        "url": None,
        "embed_url": None,
    }

    # Already on Bob's service: it opens as shared.
    bobs = client.get("/posts/", headers=bob["headers"]).json()["items"][0]["music"]
    assert bobs["native"]["status"] == "resolved"
    assert bobs["native"]["url"] == SPOTIFY_TRACK
    assert bobs["native"]["embed_url"] == (
        "https://open.spotify.com/embed/track/4cOdK2wGLETKBW3PvgPWqT"
    )


@pytest.mark.parametrize(
    ("url", "service", "player"),
    [
        (
            SOUNDCLOUD_TRACK,
            "spotify",
            "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist"
            "%2Fsome-song&visual=true&hide_related=true&show_comments=false"
            "&show_reposts=false&show_teaser=false",
        ),
        (BANDCAMP_TRACK, "apple_music", None),  # no player id scraped in tests
    ],
)
def test_untranslatable_music_stays_on_its_own_player(
    client, alice, make_post, catalogues, url, service, player
):
    post = make_post(alice["headers"], url=url)
    catalogues.requests.clear()  # posting Bandcamp reads its page for the player
    choose(client, alice, service)

    music_item = feed_music(client, alice, post)
    assert music_item["native"]["status"] == "original"
    assert music_item["embed_url"] == player

    response = native_link(client, alice, post)
    assert response.json()["status"] == "original"
    assert catalogues.requests == [] and catalogues.youtube_calls == [], (
        "nothing to look up"
    )


def test_bandcamp_player_comes_from_its_page(client, alice, monkeypatch):
    monkeypatch.setattr(
        music, "fetch_metadata", lambda link: MusicMetadata(embed_url=BANDCAMP_PLAYER)
    )

    response = client.post(
        "/posts/",
        json={
            "music_url": BANDCAMP_TRACK,
            "title": "Some Song",
            "artist_name": "Artist",
            "embed_url": "https://evil.example/player",
        },
        headers=alice["headers"],
    )

    assert response.json()["music"]["embed_url"] == BANDCAMP_PLAYER


def test_a_bandcamp_page_cannot_embed_anything_else(client, alice, monkeypatch):
    monkeypatch.setattr(
        music,
        "fetch_metadata",
        lambda link: MusicMetadata(embed_url="https://evil.example/player"),
    )

    response = client.post(
        "/posts/",
        json={"music_url": BANDCAMP_TRACK, "title": "Some Song"},
        headers=alice["headers"],
    )

    assert response.json()["music"]["embed_url"] is None


# ── Looking it up ─────────────────────────────────────────────────────────────


def test_a_lookup_is_cached_per_service(client, alice, bob, make_post, catalogues):
    post = make_post(
        alice["headers"],
        url=SPOTIFY_TRACK.replace("4cOdK2wGLETKBW3PvgPWqT", "2EqlS6tkEnglzr7tkKAAYD"),
    )
    choose(client, alice, "apple_music")
    choose(client, bob, "youtube_music")

    assert native_link(client, alice, post).json()["status"] == "resolved"
    asked = len(catalogues.requests)
    assert feed_native(client, alice, post)["status"] == "resolved"
    assert native_link(client, alice, post).json()["status"] == "resolved"
    assert len(catalogues.requests) == asked, "Alice's answer is remembered"

    # Bob's service is looked up on its own.
    assert feed_native(client, bob, post)["status"] == "pending"
    assert native_link(client, bob, post).json()["status"] == "resolved"


def test_one_service_failing_doesnt_block_the_others(
    client, alice, bob, make_post, catalogues
):
    catalogues.break_route("youtube", RuntimeError("YouTube changed its API"))
    post = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[0].releases["apple_music"])
    )
    choose(client, alice, "spotify")
    choose(client, bob, "youtube_music")

    assert native_link(client, bob, post).status_code == 503
    assert native_link(client, alice, post).json()["status"] == "resolved"
    assert feed_native(client, bob, post)["status"] == "pending"


def test_no_match_reads_as_unavailable_and_says_why_in_the_log(
    client, alice, make_post, catalogues, caplog
):
    caplog.set_level(logging.INFO, logger="src.music")
    # Only covers and a live take.
    catalogues.overrides["api.spotify.com/v1/search"] = {
        "tracks": {"items": [spotify_track(r) for r in SONGS[0].decoys["spotify"]]}
    }
    post = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[0].releases["apple_music"])
    )
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "unavailable"
    assert response.json()["url"] is None
    assert feed_native(client, alice, post)["status"] == "unavailable"
    assert "No spotify match for" in caplog.text
    assert "'Come Together - 2019 Mix'" in caplog.text


def test_a_link_its_service_doesnt_know_is_found_by_the_posts_title(
    client, alice, make_post, catalogues
):
    # The seeded Come Together: an Apple Music id Apple doesn't know.
    post = client.post(
        "/posts/",
        json={
            "music_url": "https://music.apple.com/us/album/come-together/1474815798"
            "?i=1474815817",
            "title": "Come Together",
            "artist_name": "The Beatles",
        },
        headers=alice["headers"],
    ).json()
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["url"] == SPOTIFY_TRACK.replace(
        "4cOdK2wGLETKBW3PvgPWqT", "2EqlS6tkEnglzr7tkKAAYD"
    )


def test_nothing_known_about_a_link_reads_as_unavailable(
    client, alice, catalogues
):
    # Neither Spotify nor the post (no artist) says what this is.
    post = client.post(
        "/posts/",
        json={"music_url": "https://open.spotify.com/track/0unknown"},
        headers=alice["headers"],
    ).json()
    choose(client, alice, "apple_music")

    assert native_link(client, alice, post).json()["status"] == "unavailable"
    assert catalogues.calls("itunes.apple.com/search") == []


@pytest.mark.parametrize(
    "url",
    [
        SPOTIFY_PLAYLIST,
        "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd",
        YOUTUBE_PLAYLIST,
        "https://soundcloud.com/artist/sets/demo",
        "https://open.spotify.com/artist/0oSGxfWSnnOXhD2fKuz2Gy",
    ],
)
def test_playlists_and_artist_pages_cant_be_shared(client, alice, url):
    for path in ("/posts/", "/posts/resolve-link"):
        field = "music_url" if path == "/posts/" else "url"
        response = client.post(path, json={field: url}, headers=alice["headers"])
        assert response.status_code == 422
        assert "Share a song or an album" in response.json()["detail"]


def test_a_youtube_album_search_skips_playlists(monkeypatch):
    class YouTube:
        def search(self, query, filter=None, limit=20):
            return [
                {"resultType": "album", "title": "Abbey Road",
                 "playlistId": "PLnotanalbum", "artists": [{"name": "The Beatles"}]},
                {"resultType": "album", "title": "Abbey Road",
                 "playlistId": "OLAK5uy_abbeyroad", "artists": [{"name": "The Beatles"}]},
            ]

    monkeypatch.setattr(music, "_ytmusic", YouTube)
    source = MusicMetadata(title="Abbey Road", artist_name="The Beatles")

    candidates = music._youtube_search(None, ItemType.ALBUM, source)

    assert [link.provider_item_id for link, _ in candidates] == ["OLAK5uy_abbeyroad"]


@pytest.mark.parametrize(
    "page",
    [
        '<meta property="og:video" content="https://bandcamp.com/EmbeddedPlayer/v=2/'
        'track=2436476419/size=large/linkcol=0084B4/notracklist=true/twittercard=true/">',
        '<meta name="bc-page-properties" content="{&quot;item_type&quot;:&quot;t&quot;,'
        '&quot;item_id&quot;:2436476419,&quot;tralbum_page_version&quot;:0}">',
    ],
)
def test_bandcamps_player_id_is_read_from_its_page(page):
    assert music.bandcamp_player(f"<html><head>{page}</head></html>") == (
        "https://bandcamp.com/EmbeddedPlayer/track=2436476419/size=large/"
        "tracklist=false/artwork=small/"
    )


def test_a_bandcamp_page_without_a_player_id_has_no_player():
    page = "<html><head><title>Bandcamp</title></head></html>"
    assert music.bandcamp_player(page) is None


def test_the_spotify_token_is_reused(client, alice, make_post, catalogues):
    first = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[0].releases["apple_music"])
    )
    second = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[1].releases["apple_music"])
    )
    choose(client, alice, "spotify")

    native_link(client, alice, first)
    native_link(client, alice, second)

    assert len(catalogues.calls("api.spotify.com/v1/search")) == 2
    assert len(catalogues.calls("accounts.spotify.com/api/token")) == 1


def test_missing_spotify_credentials_are_logged(
    client, alice, make_post, catalogues, monkeypatch, caplog
):
    monkeypatch.setattr(music.settings, "spotify_client_secret", None)
    post = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[0].releases["apple_music"])
    )
    choose(client, alice, "spotify")

    assert native_link(client, alice, post).status_code == 503
    assert "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET" in caplog.text
    assert feed_native(client, alice, post)["status"] == "pending"


@pytest.mark.parametrize(
    ("route", "failure", "logged"),
    [
        (
            "accounts.spotify.com/api/token",
            (400, {"error": "invalid_client"}),
            "accounts.spotify.com answered 400",
        ),
        # A search Spotify refuses is an error, not "no match".
        (
            "api.spotify.com/v1/search",
            (400, {"error": {"status": 400}}),
            "api.spotify.com answered 400",
        ),
        (
            "api.spotify.com/v1/search",
            (429, {"error": {"status": 429}}),
            "api.spotify.com answered 429",
        ),
        (
            "api.spotify.com/v1/search",
            (500, {"error": {"status": 500}}),
            "api.spotify.com answered 500",
        ),
        ("itunes.apple.com/lookup", (503, None), "itunes.apple.com answered 503"),
        ("itunes.apple.com/lookup", "<html>maintenance</html>", "Unexpected answer"),
        ("itunes.apple.com/lookup", httpx.ReadTimeout("timed out"), "unreachable"),
        ("api.spotify.com/v1/search", httpx.ConnectError("refused"), "unreachable"),
    ],
)
def test_lookup_failures_are_reported_and_retried(
    client, alice, make_post, catalogues, caplog, route, failure, logged
):
    url = source_url("apple_music", SONGS[0].releases["apple_music"])
    catalogues.break_route(route, failure)
    post = make_post(alice["headers"], url=url)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Couldn't look this up on Spotify")
    # The reason goes to the server log, not to the client.
    assert f"Lookup of {url} failed" in caplog.text
    assert logged in caplog.text
    # Not remembered as "unavailable": the next time asks again and succeeds.
    assert feed_native(client, alice, post)["status"] == "pending"
    catalogues.fix()
    assert native_link(client, alice, post).json()["status"] == "resolved"


def test_unavailable_is_asked_again_after_a_day(client, alice, make_post, catalogues):
    catalogues.overrides["api.spotify.com/v1/search"] = {"tracks": {"items": []}}
    post = make_post(
        alice["headers"], url=source_url("apple_music", SONGS[0].releases["apple_music"])
    )
    choose(client, alice, "spotify")
    assert native_link(client, alice, post).json()["status"] == "unavailable"

    with SessionLocal() as db:
        item = db.get(models.DBMusicItem, post["music"]["id"])
        item.links_resolved_at -= timedelta(days=2)
        db.commit()

    assert feed_native(client, alice, post)["status"] == "pending"
    del catalogues.overrides["api.spotify.com/v1/search"]
    assert native_link(client, alice, post).json()["status"] == "resolved"


def test_lookups_are_off_when_link_metadata_is_disabled(client, alice, make_post):
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    # conftest sets ENABLE_LINK_METADATA=false: no network, and no false "unavailable".
    assert native_link(client, alice, post).status_code == 503
    assert feed_native(client, alice, post)["status"] == "pending"


def test_native_link_needs_a_signed_in_listener_with_a_service(client, alice, make_post):
    post = make_post(alice["headers"])

    assert client.get(f"/music/{post['music']['id']}/native-link").status_code == 401
    assert native_link(client, alice, post).status_code == 400

    choose(client, alice, "apple_music")
    missing = client.get("/music/999/native-link", headers=alice["headers"])
    assert missing.status_code == 404


# ── Matching rules ────────────────────────────────────────────────────────────

APPLE_LINK = parse_music_url("https://music.apple.com/us/album/x/1?i=2")


def track(title: str, artist: str, duration_ms: int | None = 200_000) -> MusicMetadata:
    return MusicMetadata(title=title, artist_name=artist, duration_ms=duration_ms)


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        (
            track("Come Together - Remastered 2009", "The Beatles"),
            track("Come Together (Remastered 2009)", "The Beatles"),
        ),
        (
            track("Heroes - 2017 Remaster", "David Bowie"),
            track('"Heroes"', "David Bowie"),
        ),
        (
            track(
                "Get Lucky (feat. Pharrell Williams & Nile Rodgers)",
                "Daft Punk, Pharrell Williams, Nile Rodgers",
            ),
            track("Get Lucky", "Daft Punk"),
        ),
        (track("Café del Mar", "Energy 52"), track("Cafe Del Mar", "Energy 52")),
        (track("Rock & Roll", "Led Zeppelin"), track("Rock and Roll", "Led Zeppelin")),
        (track("Bohemian Rhapsody", "Queen"), track("bohemian rhapsody", "QUEEN")),
        # Punctuation and accents.
        (track("Don't Stop Me Now", "Queen"), track("Dont Stop Me Now", "Queen")),
        (track("Beyoncé - Halo", "Beyoncé"), track("Beyonce - Halo", "Beyonce")),
        # Spelled a little differently: only a fuzzy comparison accepts these.
        (
            track("Another Brick in the Wall, Pt. 2", "Pink Floyd"),
            track("Another Brick in the Wall (Part 2)", "Pink Floyd"),
        ),
        (
            track("Sgt. Pepper's Lonely Hearts Club Band", "The Beatles"),
            track("Sgt. Pepper's Lonely Heart Club Band", "The Beatles"),
        ),
        # Lengths a few seconds apart, or unknown on one side.
        (
            track("Hallelujah", "Jeff Buckley"),
            track("Hallelujah", "Jeff Buckley", 204_000),
        ),
        (track("Hallelujah", "Jeff Buckley"), track("Hallelujah", "Jeff Buckley", None)),
    ],
)
def test_the_same_song_spelled_differently_matches(source, candidate):
    match = music.best_match(source, ItemType.TRACK, [(APPLE_LINK, candidate)])
    assert match == APPLE_LINK


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        (
            track("Come Together - Remastered 2009", "The Beatles"),
            track("Come Together (2019 Mix)", "The Beatles"),
        ),
        (track("Hallelujah", "Jeff Buckley"), track("Hallelujah", "Leonard Cohen")),
        (
            track("Hallelujah", "Jeff Buckley"),
            track("Hallelujah", "Jeff Buckley", 215_000),
        ),
        (
            track("Blinding Lights", "The Weeknd"),
            track("Blinding Lights - Remix", "The Weeknd"),
        ),
        (track("", "Jeff Buckley"), track("", "Jeff Buckley")),
    ],
)
def test_different_music_does_not_match(source, candidate):
    assert music.best_match(source, ItemType.TRACK, [(APPLE_LINK, candidate)]) is None


def test_an_album_is_not_a_song():
    album = parse_music_url("https://music.apple.com/us/album/abbey-road/1441164426")
    song = track("Abbey Road", "The Beatles")
    assert music.best_match(song, ItemType.TRACK, [(album, song)]) is None


def test_the_closest_title_then_length_wins():
    album_cut = parse_music_url("https://open.spotify.com/track/album")
    compilation = parse_music_url("https://open.spotify.com/track/compilation")
    candidates = [
        (compilation, track("Come Together", "The Beatles", 202_500)),
        (album_cut, track("Come Together", "The Beatles", 200_100)),
    ]
    source = track("Come Together", "The Beatles")
    assert music.best_match(source, ItemType.TRACK, candidates) == album_cut
