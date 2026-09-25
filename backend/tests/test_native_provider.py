"""Opening shared music on the listener's own streaming service."""

from __future__ import annotations

import copy
from datetime import timedelta

import httpx
import pytest
from conftest import APPLE_ALBUM, SPOTIFY_TRACK

from src import music
from src.database import models
from src.database.database import SessionLocal

APPLE_TRACK = (
    "https://music.apple.com/us/album/never-gonna-give-you-up/1558533900?i=1558534271"
)
APPLE_TRACK_FROM_SONG_LINK = (
    APPLE_TRACK + "&uo=4&app=music&ls=1&at=1000lHKX&ct=api_http&itscg=30200&itsct=odsl_m"
)
BANDCAMP_TRACK = "https://artist.bandcamp.com/track/some-song"
SOUNDCLOUD_TRACK = "https://soundcloud.com/artist/some-song"
SPOTIFY_PLAYLIST = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# The shape song.link answers with for the Spotify track above (trimmed to the
# platforms Setlist knows plus one it ignores).
SPOTIFY_ANSWER = {
    "entityUniqueId": "SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT",
    "userCountry": "US",
    "pageUrl": "https://song.link/s/4cOdK2wGLETKBW3PvgPWqT",
    "entitiesByUniqueId": {
        "SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT": {
            "id": "4cOdK2wGLETKBW3PvgPWqT",
            "type": "song",
            "title": "Never Gonna Give You Up",
            "artistName": "Rick Astley",
            "thumbnailUrl": "https://i.scdn.co/image/ab67616d0000b273",
            "thumbnailWidth": 640,
            "thumbnailHeight": 640,
            "apiProvider": "spotify",
            "platforms": ["spotify"],
        },
        "ITUNES_SONG::1558534271": {
            "id": "1558534271",
            "type": "song",
            "title": "Never Gonna Give You Up",
            "artistName": "Rick Astley",
            "thumbnailUrl": "https://is1-ssl.mzstatic.com/image/thumb/Music/512x512bb.jpg",
            "apiProvider": "itunes",
            "platforms": ["appleMusic", "itunes"],
        },
        "DEEZER_SONG::781592622": {
            "id": "781592622",
            "type": "song",
            "title": "Never Gonna Give You Up",
            "artistName": "Rick Astley",
            "apiProvider": "deezer",
            "platforms": ["deezer"],
        },
        "AMAZON_SONG::B08WJP9KHQ": {
            "id": "B08WJP9KHQ",
            "type": "song",
            "title": "Never Gonna Give You Up",
            "artistName": "Rick Astley",
            "apiProvider": "amazon",
            "platforms": ["amazonMusic"],
        },
    },
    "linksByPlatform": {
        "spotify": {
            "country": "US",
            "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
            "nativeAppUriDesktop": "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
            "entityUniqueId": "SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT",
        },
        "appleMusic": {
            "country": "US",
            "url": APPLE_TRACK_FROM_SONG_LINK,
            "nativeAppUriMobile": "music://music.apple.com/us/album/1558533900?i=1558534271",
            "nativeAppUriDesktop": "itms://music.apple.com/us/album/1558533900?i=1558534271",
            "entityUniqueId": "ITUNES_SONG::1558534271",
        },
        "deezer": {
            "country": "US",
            "url": "https://www.deezer.com/track/781592622",
            "entityUniqueId": "DEEZER_SONG::781592622",
        },
        "amazonMusic": {
            "country": "US",
            "url": "https://music.amazon.com/albums/B08WJNW6ZR?trackAsin=B08WJP9KHQ",
            "entityUniqueId": "AMAZON_SONG::B08WJP9KHQ",
        },
    },
}

# The same song asked for from Apple Music's side.
APPLE_ANSWER = {
    "entityUniqueId": "ITUNES_SONG::1558534271",
    "userCountry": "US",
    "entitiesByUniqueId": {
        key: SPOTIFY_ANSWER["entitiesByUniqueId"][key]
        for key in ("ITUNES_SONG::1558534271", "SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT")
    },
    "linksByPlatform": {
        "appleMusic": SPOTIFY_ANSWER["linksByPlatform"]["appleMusic"],
        "spotify": {
            "country": "US",
            "url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT?si=from-song-link",
            "entityUniqueId": "SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT",
        },
    },
}


def answer_with(**apple_entity) -> dict:
    """SPOTIFY_ANSWER with the Apple Music match's metadata changed."""
    payload = copy.deepcopy(SPOTIFY_ANSWER)
    payload["entitiesByUniqueId"]["ITUNES_SONG::1558534271"].update(apple_entity)
    return payload


class FakeSongLink:
    """Stands in for api.song.link: records requests, replays one answer."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.reply(200, SPOTIFY_ANSWER)

    def reply(self, status: int, payload=None, *, text: str | None = None) -> None:
        def respond(_request):
            if text is not None:
                return httpx.Response(status, text=text)
            return httpx.Response(status, json=payload)

        self._respond = respond

    def fail(self, error: Exception) -> None:
        def respond(_request):
            raise error

        self._respond = respond

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._respond(request)


@pytest.fixture
def song_link(monkeypatch) -> FakeSongLink:
    fake = FakeSongLink()
    monkeypatch.setattr(music.settings, "enable_link_metadata", True)
    monkeypatch.setattr(
        music,
        "_client",
        lambda timeout=None: httpx.Client(transport=httpx.MockTransport(fake.handle)),
    )
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
    ],
)
def test_untranslatable_music_stays_on_its_own_link(
    client, alice, make_post, song_link, url, service
):
    post = make_post(alice["headers"], url=url)
    choose(client, alice, service)

    assert feed_native(client, alice, post)["status"] == "original"

    response = native_link(client, alice, post)
    assert response.status_code == 200
    assert response.json()["status"] == "original"
    assert response.json()["url"] is None
    assert song_link.requests == [], "nothing to look up"


# ── Looking it up ─────────────────────────────────────────────────────────────


def test_spotify_track_opens_on_apple_music(client, alice, make_post, song_link):
    post = make_post(alice["headers"], url=SPOTIFY_TRACK)
    choose(client, alice, "apple_music")

    response = native_link(client, alice, post)

    assert response.status_code == 200
    assert response.json() == {
        "status": "resolved",
        "provider": "apple_music",
        "provider_name": "Apple Music",
        "url": APPLE_TRACK_FROM_SONG_LINK,
    }
    assert song_link.requests[0].url.params["url"] == SPOTIFY_TRACK

    # Cached: the timeline knows it now, and nobody asks song.link again.
    assert feed_native(client, alice, post)["url"] == APPLE_TRACK_FROM_SONG_LINK
    assert native_link(client, alice, post).json()["status"] == "resolved"
    assert len(song_link.requests) == 1


def test_one_lookup_serves_every_service(client, alice, bob, make_post, song_link):
    post = make_post(alice["headers"], url=SPOTIFY_TRACK)
    choose(client, alice, "apple_music")
    choose(client, bob, "deezer")

    native_link(client, alice, post)

    assert feed_native(client, bob, post) == {
        "status": "resolved",
        "provider": "deezer",
        "provider_name": "Deezer",
        "url": "https://www.deezer.com/track/781592622",
    }
    assert len(song_link.requests) == 1


def test_apple_music_track_opens_on_spotify(client, alice, make_post, song_link):
    song_link.reply(200, APPLE_ANSWER)
    post = make_post(alice["headers"], url=APPLE_TRACK)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "resolved"
    # Run through the same parser as pasted links, so tracking is stripped.
    assert response.json()["url"] == SPOTIFY_TRACK


def test_no_match_reads_as_unavailable(client, alice, make_post, song_link):
    payload = copy.deepcopy(SPOTIFY_ANSWER)
    del payload["linksByPlatform"]["appleMusic"]
    song_link.reply(200, payload)
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "unavailable"
    assert response.json()["url"] is None
    assert feed_native(client, alice, post)["status"] == "unavailable"


@pytest.mark.parametrize(
    "apple_entity",
    [
        # A cover by someone else.
        {"artistName": "Some Tribute Band"},
        # A different recording that song.link offered as the closest thing.
        {"title": "Never Gonna Give You Up (Live at Wembley)"},
        # An album offered for a song.
        {"type": "album"},
        # Nothing to compare against.
        {"title": None, "artistName": None},
    ],
)
def test_a_doubtful_match_is_not_trusted(
    client, alice, make_post, song_link, apple_entity
):
    song_link.reply(200, answer_with(**apple_entity))
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    assert native_link(client, alice, post).json()["status"] == "unavailable"


def test_missing_original_metadata_is_not_trusted(client, alice, make_post, song_link):
    payload = copy.deepcopy(SPOTIFY_ANSWER)
    del payload["entitiesByUniqueId"]["SPOTIFY_SONG::4cOdK2wGLETKBW3PvgPWqT"]
    song_link.reply(200, payload)
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    assert native_link(client, alice, post).json()["status"] == "unavailable"


def test_music_song_link_does_not_know_reads_as_unavailable(
    client, alice, make_post, song_link
):
    song_link.reply(400, {"statusCode": 400, "code": "could_not_resolve_entity"})
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    assert native_link(client, alice, post).json()["status"] == "unavailable"


@pytest.mark.parametrize(
    "failure",
    [
        ("reply", 429, {"statusCode": 429, "code": "too_many_requests"}),
        ("reply", 500, {"statusCode": 500}),
        ("reply", 503, None),
        ("text", 200, "<html>maintenance</html>"),
        ("reply", 200, {"entityUniqueId": "x", "entitiesByUniqueId": ["not a map"]}),
        ("fail", httpx.ReadTimeout("timed out")),
        ("fail", httpx.ConnectError("connection refused")),
    ],
)
def test_lookup_failures_are_reported_and_retried(
    client, alice, make_post, song_link, failure, caplog
):
    kind, *args = failure
    if kind == "reply":
        song_link.reply(*args)
    elif kind == "text":
        song_link.reply(args[0], text=args[1])
    else:
        song_link.fail(args[0])
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")

    response = native_link(client, alice, post)

    assert response.status_code == 503
    assert response.json()["detail"].startswith("Couldn't look this up on Apple Music")
    # The reason goes to the server log, not to the client.
    assert f"Lookup of {SPOTIFY_TRACK} failed: song.link" in caplog.text
    # Not remembered as "unavailable": the next tap asks again and succeeds.
    assert feed_native(client, alice, post)["status"] == "pending"
    song_link.reply(200, SPOTIFY_ANSWER)
    assert native_link(client, alice, post).json()["status"] == "resolved"


def test_unavailable_is_asked_again_after_a_day(client, alice, make_post, song_link):
    payload = copy.deepcopy(SPOTIFY_ANSWER)
    del payload["linksByPlatform"]["appleMusic"]
    song_link.reply(200, payload)
    post = make_post(alice["headers"])
    choose(client, alice, "apple_music")
    native_link(client, alice, post)

    with SessionLocal() as db:
        item = db.get(models.DBMusicItem, post["music"]["id"])
        item.links_resolved_at -= timedelta(days=2)
        db.commit()

    assert feed_native(client, alice, post)["status"] == "pending"
    song_link.reply(200, SPOTIFY_ANSWER)
    assert native_link(client, alice, post).json()["status"] == "resolved"
    assert len(song_link.requests) == 2


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


def test_come_together_on_apple_music_opens_for_a_spotify_listener(
    client, alice, make_post, song_link
):
    apple = "https://music.apple.com/us/album/come-together/1441164426?i=1441164430"
    spotify = "https://open.spotify.com/track/2EqlS6tkEnglzr7tkKAAYD"
    song_link.reply(
        200,
        {
            "entityUniqueId": "ITUNES_SONG::1441164430",
            "entitiesByUniqueId": {
                "ITUNES_SONG::1441164430": {
                    "type": "song",
                    "title": "Come Together",
                    "artistName": "The Beatles",
                },
                "SPOTIFY_SONG::2EqlS6tkEnglzr7tkKAAYD": {
                    "type": "song",
                    "title": "Come Together - Remastered 2009",
                    "artistName": "The Beatles",
                },
            },
            "linksByPlatform": {
                "appleMusic": {"url": apple, "entityUniqueId": "ITUNES_SONG::1441164430"},
                "spotify": {
                    "url": spotify,
                    "entityUniqueId": "SPOTIFY_SONG::2EqlS6tkEnglzr7tkKAAYD",
                },
            },
        },
    )
    post = make_post(alice["headers"], url=apple)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["status"] == "resolved"
    assert response.json()["url"] == spotify


def test_album_on_apple_music_opens_on_spotify(client, alice, make_post, song_link):
    song_link.reply(
        200,
        {
            "entityUniqueId": "ITUNES_ALBUM::1474815798",
            "entitiesByUniqueId": {
                "ITUNES_ALBUM::1474815798": {
                    "type": "album",
                    "title": "Abbey Road (Remastered)",
                    "artistName": "The Beatles",
                },
                "SPOTIFY_ALBUM::0ETFjACtuP2ADo6LFhL6HN": {
                    "type": "album",
                    "title": "Abbey Road - Remastered",
                    "artistName": "The Beatles",
                },
            },
            "linksByPlatform": {
                "spotify": {
                    "url": "https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN",
                    "entityUniqueId": "SPOTIFY_ALBUM::0ETFjACtuP2ADo6LFhL6HN",
                },
            },
        },
    )
    post = make_post(alice["headers"], url=APPLE_ALBUM)
    choose(client, alice, "spotify")

    response = native_link(client, alice, post)

    assert response.json()["url"] == "https://open.spotify.com/album/0ETFjACtuP2ADo6LFhL6HN"


# ── Matching rules ────────────────────────────────────────────────────────────


def _pair(source: dict, match: dict, url: str = APPLE_TRACK) -> dict:
    return {
        "entityUniqueId": "SPOTIFY_SONG::a",
        "entitiesByUniqueId": {
            "SPOTIFY_SONG::a": {"type": "song", **source},
            "ITUNES_SONG::b": {"type": "song", **match},
        },
        "linksByPlatform": {
            "appleMusic": {"url": url, "entityUniqueId": "ITUNES_SONG::b"},
        },
    }


@pytest.mark.parametrize(
    ("source", "match"),
    [
        (
            {"title": "Come Together - Remastered 2009", "artistName": "The Beatles"},
            {"title": "Come Together (Remastered 2009)", "artistName": "The Beatles"},
        ),
        # Spotify tags remasters, Apple Music usually doesn't.
        (
            {"title": "Come Together - Remastered 2009", "artistName": "The Beatles"},
            {"title": "Come Together", "artistName": "The Beatles"},
        ),
        (
            {"title": "Heroes - 2017 Remaster", "artistName": "David Bowie"},
            {"title": "\"Heroes\"", "artistName": "David Bowie"},
        ),
        (
            {"title": "Get Lucky (feat. Pharrell Williams & Nile Rodgers)",
             "artistName": "Daft Punk, Pharrell Williams, Nile Rodgers"},
            {"title": "Get Lucky", "artistName": "Daft Punk"},
        ),
        (
            {"title": "Café del Mar", "artistName": "Energy 52"},
            {"title": "Cafe Del Mar", "artistName": "Energy 52"},
        ),
        (
            {"title": "Bohemian Rhapsody", "artistName": "Queen"},
            {"title": "bohemian rhapsody", "artistName": "QUEEN"},
        ),
    ],
)
def test_the_same_song_spelled_differently_matches(source, match):
    assert music.verified_links(_pair(source, match)) == {"apple_music": APPLE_TRACK}


@pytest.mark.parametrize(
    ("source", "match", "url"),
    [
        # Different version.
        (
            {"title": "Come Together - Remastered 2009", "artistName": "The Beatles"},
            {"title": "Come Together (2019 Mix)", "artistName": "The Beatles"},
            APPLE_TRACK,
        ),
        # Same title, different artist: a cover.
        (
            {"title": "Hallelujah", "artistName": "Jeff Buckley"},
            {"title": "Hallelujah", "artistName": "Leonard Cohen"},
            APPLE_TRACK,
        ),
        # The "Apple Music" link isn't one.
        (
            {"title": "Hallelujah", "artistName": "Jeff Buckley"},
            {"title": "Hallelujah", "artistName": "Jeff Buckley"},
            "https://example.com/hallelujah",
        ),
        # Nor is this one (it's Spotify).
        (
            {"title": "Hallelujah", "artistName": "Jeff Buckley"},
            {"title": "Hallelujah", "artistName": "Jeff Buckley"},
            "https://open.spotify.com/track/abc",
        ),
    ],
)
def test_different_music_or_bad_links_do_not_match(source, match, url):
    assert music.verified_links(_pair(source, match, url)) == {}


def test_empty_or_malformed_answers_find_nothing():
    assert music.verified_links({}) == {}
    assert music.verified_links({"entityUniqueId": "x", "linksByPlatform": None}) == {}
