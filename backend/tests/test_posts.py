"""Posts always carry music."""

from conftest import APPLE_ALBUM, SPOTIFY_TRACK


def test_creating_a_post_requires_a_music_link(client, alice):
    missing = client.post("/posts/", json={"caption": "just words"}, headers=alice["headers"])
    assert missing.status_code == 422

    not_music = client.post(
        "/posts/",
        json={"music_url": "https://example.com/a-photo.jpg", "caption": "hi"},
        headers=alice["headers"],
    )
    assert not_music.status_code == 422
    assert "Spotify" in not_music.json()["detail"]


def test_creating_a_post_requires_auth(client):
    assert client.post("/posts/", json={"music_url": SPOTIFY_TRACK}).status_code == 401


def test_create_post_returns_music_payload(client, alice):
    response = client.post(
        "/posts/",
        json={
            "music_url": SPOTIFY_TRACK,
            "caption": "best song ever",
            "title": "Bohemian Rhapsody",
            "artist_name": "Queen",
        },
        headers=alice["headers"],
    )
    assert response.status_code == 201
    post = response.json()

    assert post["caption"] == "best song ever"
    assert post["author"]["username"] == "alice"
    assert post["music"]["provider"] == "spotify"
    assert post["music"]["provider_name"] == "Spotify"
    assert post["music"]["item_type"] == "track"
    assert post["music"]["title"] == "Bohemian Rhapsody"
    assert post["music"]["artist_name"] == "Queen"
    assert post["likes_count"] == 0
    assert post["comments_count"] == 0
    assert post["is_liked"] is False


def test_caption_is_optional(client, alice):
    response = client.post(
        "/posts/", json={"music_url": APPLE_ALBUM}, headers=alice["headers"]
    )
    assert response.status_code == 201
    assert response.json()["caption"] == ""
    # Without a metadata lookup we still show something sensible.
    assert response.json()["music"]["title"] == "Abbey Road 2019 Mix"


def test_the_same_track_is_stored_once(client, alice, bob):
    first = client.post(
        "/posts/", json={"music_url": SPOTIFY_TRACK}, headers=alice["headers"]
    ).json()
    second = client.post(
        "/posts/",
        json={"music_url": SPOTIFY_TRACK + "?si=tracking-parameter"},
        headers=bob["headers"],
    ).json()

    assert first["id"] != second["id"]
    assert first["music"]["id"] == second["music"]["id"]


def test_resolve_link_previews_a_paste(client, alice):
    response = client.post(
        "/posts/resolve-link", json={"url": SPOTIFY_TRACK}, headers=alice["headers"]
    )
    assert response.status_code == 200
    assert response.json()["provider_name"] == "Spotify"
    assert response.json()["item_type"] == "track"

    bad = client.post(
        "/posts/resolve-link", json={"url": "nonsense"}, headers=alice["headers"]
    )
    assert bad.status_code == 422


def test_post_detail_includes_comments(client, alice, make_post):
    post = make_post(alice["headers"])
    client.post(
        f"/posts/{post['id']}/comments", json={"content": "so good"}, headers=alice["headers"]
    )

    detail = client.get(f"/posts/{post['id']}").json()
    assert detail["comments_count"] == 1
    assert detail["comments"][0]["content"] == "so good"
    assert detail["comments"][0]["author"]["username"] == "alice"


def test_only_the_author_can_edit_or_delete(client, alice, bob, make_post):
    post = make_post(alice["headers"])

    assert client.patch(
        f"/posts/{post['id']}", json={"caption": "nope"}, headers=bob["headers"]
    ).status_code == 403
    assert client.delete(f"/posts/{post['id']}", headers=bob["headers"]).status_code == 403

    edited = client.patch(
        f"/posts/{post['id']}", json={"caption": "second thoughts"}, headers=alice["headers"]
    )
    assert edited.json()["caption"] == "second thoughts"

    assert client.delete(f"/posts/{post['id']}", headers=alice["headers"]).status_code == 204
    assert client.get(f"/posts/{post['id']}").status_code == 404


def test_profile_posts_and_counts(client, alice, make_post):
    make_post(alice["headers"], caption="one")
    make_post(alice["headers"], url=APPLE_ALBUM, caption="two")

    posts = client.get(f"/users/{alice['user']['id']}/posts").json()
    assert posts["total"] == 2
    assert [post["caption"] for post in posts["items"]] == ["two", "one"]

    profile = client.get(f"/users/{alice['user']['id']}").json()
    assert profile["posts_count"] == 2


def test_pagination(client, alice, make_post):
    for index in range(5):
        make_post(alice["headers"], caption=f"post {index}")

    first = client.get("/posts/", params={"limit": 2, "offset": 0}).json()
    assert len(first["items"]) == 2
    assert first["total"] == 5
    assert first["has_more"] is True

    last = client.get("/posts/", params={"limit": 2, "offset": 4}).json()
    assert len(last["items"]) == 1
    assert last["has_more"] is False
