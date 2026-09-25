"""Opening shared music on the listener's own streaming service."""

from __future__ import annotations

import copy
from datetime import timedelta

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
DEEZER_TRACK = "https://www.deezer.com/track/3135556"

APPLE_COME_TOGETHER = "https://music.apple.com/us/album/come-together/1441164426?i=1441164430"
SPOTIFY_COME_TOGETHER = "https://open.spotify.com/track/2EqlS6tkEnglzr7tkKAAYD"
APPLE_ABBEY_ROAD = "https://music.apple.com/us/album/abbey-road-remastered/1441164426"
APPLE_RICK = (
    "https://music.apple.com/us/album/never-gonna-give-you-up/1558533900?i=1558534271"
)

# ── What the services answer (trimmed to the fields that matter) ─────────────

SPOTIFY_TOKEN = {
    "access_token": "BQD-app-token", "token_type": "Bearer", "expires_in": 3600
}


def spotify_track(track_id: str, name: str, artists: list[str], duration_ms: int) -> dict:
    return {
        "album": {"album_type": "album", "name": "Some Album"},
        "artists": [{"name": artist, "type": "artist"} for artist in artists],
        "duration_ms": duration_ms,
        "external_ids": {"isrc": "GBAYE0601690"},
        "external_urls": {"spotify": f"https://open.spotify.com/track/{track_id}"},
        "id": track_id,
        "name": name,
        "type": "track",
        "uri": f"spotify:track:{track_id}",
    }


def spotify_album(album_id: str, name: str, artist: str) -> dict:
    return {
        "album_type": "album",
        "artists": [{"name": artist, "type": "artist"}],
        "external_urls": {"spotify": f"https://open.spotify.com/album/{album_id}"},
        "id": album_id,
        "name": name,
        "total_tracks": 17,
        "type": "album",
    }


def itunes_song(track_id: int, name: str, artist: str, millis: int) -> dict:
    url = f"https://music.apple.com/us/album/{name.lower().replace(' ', '-')}/1441164426"
    return {
        "wrapperType": "track",
        "kind": "song",
        "artistName": artist,
        "collectionName": "Some Album",
        "trackName": name,
        "trackId": track_id,
        "collectionViewUrl": f"{url}?i={track_id}&uo=4",
        "trackViewUrl": f"{url}?i={track_id}&uo=4",
        "trackTimeMillis": millis,
        "country": "USA",
    }


def itunes(*results: dict) -> dict:
    return {"resultCount": len(results), "results": list(results)}


def spotify_search(kind: str, *items: dict) -> dict:
    return {kind: {"items": list(items), "limit": 10, "offset": 0, "total": len(items)}}


COME_TOGETHER_ON_APPLE = itunes(
    itunes_song(1441164430, "Come Together", "The Beatles", 259947)
)
COME_TOGETHER_ON_SPOTIFY = spotify_search(
    "tracks",
    spotify_track("0mix2019", "Come Together - 2019 Mix", ["The Beatles"], 259_000),
    spotify_track("0cover", "Come Together", ["Aerosmith"], 225_000),
    spotify_track("2EqlS6tkEnglzr7tkKAAYD", "Come Together - Remastered 2009",
                  ["The Beatles"], 259_946),
)


class FakeCatalogues:
    """Answers like Spotify's Web API and Apple's iTunes Search API."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.routes: dict = {}
        self.reply("accounts.spotify.com/api/token", 200, SPOTIFY_TOKEN)

    def reply(self, route: str, status: int, payload=None, *, text: str | None = None):
        def respond(_request):
            if text is not None:
                return httpx.Response(status, text=text)
            return httpx.Response(status, json=payload)

        self.routes[route] = respond

    def fail(self, route: str, error: Exception) -> None:
        def respond(_request):
            raise error

        self.routes[route] = respond

    def calls(self, route: str) -> list[httpx.Request]:
        return [r for r in self.requests if (r.url.host + r.url.path).startswith(route)]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        for route, respond in self.routes.items():
            if (request.url.host + request.url.path).startswith(route):
                return respond(request)
        return httpx.Response(404, json={"error": {"status": 404}})


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
    return fake


def come_together(catalogues: FakeCatalogues) -> None:
    catalogues.reply("itunes.apple.com/lookup", 200, COME_TOGETHER_ON_APPLE)
    catalogues.reply("api.spotify.com/v1/search", 200, COME_TOGETHER_ON_SPOTIFY)


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


def feed_native(client, user: dict, post: dict) -> dict | None:
    detail = client.get(f"/posts/{post['id']}", headers=user["headers"]).json()
    return detail["music"]["native"]


# ── Choosing a service ────────────────────────────────────────────────────────


def test_native_provider_is_saved_on_the_account(client, alice):
    me = client.get("/users/me", headers=alice["headers"]).json()
    assert me["native_provider"] is None

    assert choose(client, alice, "apple_music")["native_provider"] == "apple_music"
    assert (
        client.get("/users/me", headers=alice["headers"]).json()["native_provider"]
        == "apple_music"
    )
    # It is a private setting, not part of the public profile.
    assert "native_provider" not in client.get(f"/users/{alice['user']['id']}").json()


def test_native_provider_can_be_cleared(client, alice):
    choose(client, alice, "spotify")
    assert choose(client, alice, "")["native_provider"] is None


def test_unknown_native_provider_is_rejected(client, alice):
    response = client.patch(
        "/users/me", json={"native_provider": "napster"}, headers=alice["headers"]
    )
    assert response.status_code == 422
    assert "Unknown music service" in response.text


def test_editing_the_profile_keeps_the_native_provider(client, alice):
    choose(client, alice, "apple_music")
    response = client.patch("/users/me", json={"bio": "hi"}, headers=alice["headers"])
    assert response.json()["native_provider"] == "apple_music"


# ── What posts say before anything is looked up ───────────────────────────────


def test_without_a_native_provider_posts_are_unchanged(client, alice, make_post):
    post = make_post(alice["headers"])

    assert post["music"]["native"] is None
    assert feed_native(client, alice, post) is None
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
    }

    # Already on Bob's service: it opens as shared.
    bobs = client.get("/posts/", headers=bob["headers"]).json()["items"][0]["music"]
    assert bobs["native"]["status"] == "resolved"
    assert bobs["native"]["url"] == SPOTIFY_TRACK


@pytest.mark.parametrize(
    ("url", "service"),
    [
        (BANDCAMP_TRACK, "apple_music"),
        (SOUNDCLOUD_TRACK, "spotify"),
        (SPOTIFY_PLAYLIST, "apple_music"),
        (SPOTIFY_TRACK, "bandcamp"),
        (DEEZER_TRACK, "spotify"),
        (SPOTIFY_TRACK, "youtube_music"),
    ],
)
def test_untranslatable_music_stays_on_its_own_link(
    client, alice, make_post, catalogues, url, service
):
    post = make_post(alice["headers"], url=url)
    choose(client, alice, service)

    assert feed_native(client, alice, post)["status"] == "original"

    response = native_link(client, alice, post)
    assert response.status_code == 200
    assert response.json()["status"] == "original"
    assert response.json()["url"] is None
    assert catalogues.requests == [], "nothing to look up"


# ── Looking it up ─────────────────────────────────────────────────────────────


def test_come_together_on_apple_music_opens_for_a_spotify_listener(
    client, alice, make_post, catalogues
):
    come_together(catalogues)
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    # The remaster, not the 2019 mix or Aerosmith's cover.
    assert response.json() == {
        "status": "resolved",
        "provider": "spotify",
        "provider_name": "Spotify",
        "url": SPOTIFY_COME_TOGETHER,
    }
    lookup = catalogues.calls("itunes.apple.com/lookup")[0]
    assert lookup.url.params["id"] == "1441164430"
    assert lookup.url.params["country"] == "us"
    search = catalogues.calls("api.spotify.com/v1/search")[0]
    assert search.url.params["q"] == 'track:"Come Together" artist:"The Beatles"'
    assert search.headers["Authorization"] == "Bearer BQD-app-token"


def test_spotify_track_opens_on_apple_music(client, alice, make_post, catalogues):
    catalogues.reply(
        "api.spotify.com/v1/tracks/4cOdK2wGLETKBW3PvgPWqT",
        200,
        spotify_track("4cOdK2wGLETKBW3PvgPWqT", "Never Gonna Give You Up",
                      ["Rick Astley"], 213_573),
    )
    catalogues.reply(
        "itunes.apple.com/search",
        200,
        itunes(
            itunes_song(1, "Never Gonna Give You Up (Karaoke Version)", "Party Band",
                        213_000),
            itunes_song(2, "Never Gonna Give You Up", "Rick Astley", 250_000),  # live
            itunes_song(1558534271, "Never Gonna Give You Up", "Rick Astley", 213_573),
        ),
    )
    post = make_post(alice["headers"], url=SPOTIFY_TRACK)
    choose(client, alice, "apple_music")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "resolved"
    assert "i=1558534271" in response.json()["url"]
    search = catalogues.calls("itunes.apple.com/search")[0]
    assert search.url.params["term"] == "Rick Astley Never Gonna Give You Up"
    assert search.url.params["entity"] == "song"

    # Cached: the timeline knows it now, and nobody is asked again.
    asked = len(catalogues.requests)
    assert feed_native(client, alice, post)["url"] == response.json()["url"]
    assert native_link(client, alice, post).json()["status"] == "resolved"
    assert len(catalogues.requests) == asked


def test_album_on_apple_music_opens_on_spotify(client, alice, make_post, catalogues):
    catalogues.reply(
        "itunes.apple.com/lookup",
        200,
        itunes({
            "wrapperType": "collection",
            "collectionType": "Album",
            "artistName": "The Beatles",
            "collectionName": "Abbey Road (Remastered)",
            "collectionViewUrl": APPLE_ABBEY_ROAD + "?uo=4",
            "trackCount": 17,
        }),
    )
    catalogues.reply(
        "api.spotify.com/v1/search",
        200,
        spotify_search(
            "albums",
            spotify_album("0deluxe", "Abbey Road (Super Deluxe Edition)", "The Beatles"),
            spotify_album(
                "0ETFjACtuP2ADo6LFhL6HN", "Abbey Road (Remastered)", "The Beatles"
            ),
        ),
    )
    post = make_post(alice["headers"], url=APPLE_ABBEY_ROAD)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["url"] == "https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN"
    search = catalogues.calls("api.spotify.com/v1/search")[0]
    assert search.url.params["q"] == 'album:"Abbey Road" artist:"The Beatles"'
    assert search.url.params["type"] == "album"


def test_no_match_reads_as_unavailable(client, alice, make_post, catalogues):
    come_together(catalogues)
    catalogues.reply(
        "api.spotify.com/v1/search",
        200,
        spotify_search("tracks", spotify_track("0cover", "Come Together", ["Aerosmith"],
                                               225_000)),
    )
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "unavailable"
    assert response.json()["url"] is None
    assert feed_native(client, alice, post)["status"] == "unavailable"


@pytest.mark.parametrize(
    "candidate",
    [
        # A cover by someone else.
        {"artists": [{"name": "Some Tribute Band"}]},
        # A different recording.
        {"name": "Come Together - Live"},
        # Same title and artist, but 20 seconds longer: another take.
        {"duration_ms": 279_946},
    ],
)
def test_a_doubtful_match_is_not_trusted(client, alice, make_post, catalogues, candidate):
    come_together(catalogues)
    only = copy.deepcopy(COME_TOGETHER_ON_SPOTIFY["tracks"]["items"][2])
    only.update(candidate)
    catalogues.reply("api.spotify.com/v1/search", 200, spotify_search("tracks", only))
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")

    assert native_link(client, alice, post).json()["status"] == "unavailable"


@pytest.mark.parametrize(
    ("url", "service", "route", "answer"),
    [
        # Spotify doesn't know the track.
        (SPOTIFY_TRACK, "apple_music", "api.spotify.com/v1/tracks/", None),
        # Neither does Apple.
        (APPLE_COME_TOGETHER, "spotify", "itunes.apple.com/lookup", itunes()),
        # Apple knows it, but without an artist there's nothing to check against.
        (
            APPLE_COME_TOGETHER,
            "spotify",
            "itunes.apple.com/lookup",
            itunes({**COME_TOGETHER_ON_APPLE["results"][0], "artistName": None}),
        ),
    ],
)
def test_missing_original_metadata_reads_as_unavailable(
    client, alice, make_post, catalogues, url, service, route, answer
):
    come_together(catalogues)
    if answer is None:
        catalogues.reply(route, 404, {"error": {"status": 404}})
    else:
        catalogues.reply(route, 200, answer)
    post = make_post(alice["headers"], url=url)
    choose(client, alice, service)

    assert native_link(client, alice, post).json()["status"] == "unavailable"
    assert catalogues.calls("api.spotify.com/v1/search") == []
    assert catalogues.calls("itunes.apple.com/search") == []


def test_the_spotify_token_is_reused(client, alice, make_post, catalogues):
    come_together(catalogues)
    first = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    second = make_post(
        alice["headers"], url="https://music.apple.com/us/song/come-together/1441164999"
    )
    choose(client, alice, "spotify")

    native_link(client, alice, first)
    native_link(client, alice, second)

    assert len(catalogues.calls("api.spotify.com/v1/search")) == 2
    token = catalogues.calls("accounts.spotify.com/api/token")
    assert len(token) == 1
    assert token[0].headers["Authorization"].startswith("Basic ")
    assert token[0].content == b"grant_type=client_credentials"


def test_missing_spotify_credentials_are_logged(
    client, alice, make_post, catalogues, monkeypatch, caplog
):
    come_together(catalogues)
    monkeypatch.setattr(music.settings, "spotify_client_secret", None)
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")

    assert native_link(client, alice, post).status_code == 503
    assert "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET" in caplog.text
    assert feed_native(client, alice, post)["status"] == "pending"


@pytest.mark.parametrize(
    ("route", "failure", "logged"),
    [
        ("accounts.spotify.com/api/token", (400, {"error": "invalid_client"}),
         "accounts.spotify.com answered 400"),
        ("api.spotify.com/v1/search", (429, {"error": {"status": 429}}),
         "api.spotify.com answered 429"),
        ("api.spotify.com/v1/search", (500, {"error": {"status": 500}}),
         "api.spotify.com answered 500"),
        ("itunes.apple.com/lookup", (503, None), "itunes.apple.com answered 503"),
        ("itunes.apple.com/lookup", "<html>maintenance</html>", "Unexpected answer"),
        ("itunes.apple.com/lookup", httpx.ReadTimeout("timed out"), "unreachable"),
        ("api.spotify.com/v1/search", httpx.ConnectError("refused"), "unreachable"),
    ],
)
def test_lookup_failures_are_reported_and_retried(
    client, alice, make_post, catalogues, caplog, route, failure, logged
):
    come_together(catalogues)
    if isinstance(failure, Exception):
        catalogues.fail(route, failure)
    elif isinstance(failure, str):
        catalogues.reply(route, 200, text=failure)
    else:
        catalogues.reply(route, *failure)
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Couldn't look this up on Spotify")
    # The reason goes to the server log, not to the client.
    assert f"Lookup of {APPLE_COME_TOGETHER} failed" in caplog.text
    assert logged in caplog.text
    # Not remembered as "unavailable": the next tap asks again and succeeds.
    assert feed_native(client, alice, post)["status"] == "pending"
    catalogues.reply("accounts.spotify.com/api/token", 200, SPOTIFY_TOKEN)
    come_together(catalogues)
    assert native_link(client, alice, post).json()["status"] == "resolved"


def test_unavailable_is_asked_again_after_a_day(client, alice, make_post, catalogues):
    come_together(catalogues)
    catalogues.reply("api.spotify.com/v1/search", 200, spotify_search("tracks"))
    post = make_post(alice["headers"], url=APPLE_COME_TOGETHER)
    choose(client, alice, "spotify")
    assert native_link(client, alice, post).json()["status"] == "unavailable"

    with SessionLocal() as db:
        item = db.get(models.DBMusicItem, post["music"]["id"])
        item.links_resolved_at -= timedelta(days=2)
        db.commit()

    assert feed_native(client, alice, post)["status"] == "pending"
    come_together(catalogues)
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

APPLE_LINK = parse_music_url(APPLE_COME_TOGETHER)


def track(title: str, artist: str, duration_ms: int | None = 200_000) -> MusicMetadata:
    return MusicMetadata(title=title, artist_name=artist, duration_ms=duration_ms)


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        (
            track("Come Together - Remastered 2009", "The Beatles"),
            track("Come Together (Remastered 2009)", "The Beatles"),
        ),
        # Spotify tags remasters, Apple Music usually doesn't.
        (
            track("Come Together - Remastered 2009", "The Beatles"),
            track("Come Together", "The Beatles", 201_500),
        ),
        (
            track("Heroes - 2017 Remaster", "David Bowie"),
            track('"Heroes"', "David Bowie"),
        ),
        (
            track("Get Lucky (feat. Pharrell Williams & Nile Rodgers)",
                  "Daft Punk, Pharrell Williams, Nile Rodgers"),
            track("Get Lucky", "Daft Punk"),
        ),
        (track("Café del Mar", "Energy 52"), track("Cafe Del Mar", "Energy 52")),
        (track("Bohemian Rhapsody", "Queen"), track("bohemian rhapsody", "QUEEN")),
        # A length on only one side isn't held against it.
        (track("Bohemian Rhapsody", "Queen"), track("Bohemian Rhapsody", "Queen", None)),
    ],
)
def test_the_same_song_spelled_differently_matches(source, candidate):
    match = music.best_match(source, ItemType.TRACK, [(APPLE_LINK, candidate)])
    assert match == APPLE_LINK


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        # Different mix.
        (
            track("Come Together - Remastered 2009", "The Beatles"),
            track("Come Together (2019 Mix)", "The Beatles"),
        ),
        # Same title, different artist: a cover.
        (track("Hallelujah", "Jeff Buckley"), track("Hallelujah", "Leonard Cohen")),
        # Same title and artist, 10 seconds apart: an edit or another take.
        (
            track("Hallelujah", "Jeff Buckley"),
            track("Hallelujah", "Jeff Buckley", 210_000),
        ),
        # Nothing to compare.
        (track("", "Jeff Buckley"), track("", "Jeff Buckley")),
    ],
)
def test_different_music_does_not_match(source, candidate):
    assert music.best_match(source, ItemType.TRACK, [(APPLE_LINK, candidate)]) is None


def test_an_album_is_not_a_song():
    album = parse_music_url(APPLE_ABBEY_ROAD)
    song = track("Abbey Road", "The Beatles")
    assert music.best_match(song, ItemType.TRACK, [(album, song)]) is None


def test_the_closest_length_wins():
    album_cut = parse_music_url("https://open.spotify.com/track/album")
    compilation = parse_music_url("https://open.spotify.com/track/compilation")
    candidates = [
        (compilation, track("Come Together", "The Beatles", 202_500)),
        (album_cut, track("Come Together", "The Beatles", 200_100)),
    ]
    assert music.best_match(track("Come Together", "The Beatles"), ItemType.TRACK,
                            candidates) == album_cut
