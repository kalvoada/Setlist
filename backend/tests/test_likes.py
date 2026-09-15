"""Likes."""


def test_like_and_unlike(client, alice, bob, make_post):
    post = make_post(alice["headers"])

    liked = client.post(f"/posts/{post['id']}/like", headers=bob["headers"])
    assert liked.status_code == 200
    assert liked.json() == {"post_id": post["id"], "is_liked": True, "likes_count": 1}

    # Liking twice keeps the count at one.
    assert client.post(
        f"/posts/{post['id']}/like", headers=bob["headers"]
    ).json()["likes_count"] == 1

    unliked = client.delete(f"/posts/{post['id']}/like", headers=bob["headers"])
    assert unliked.json() == {"post_id": post["id"], "is_liked": False, "likes_count": 0}

    # Unliking something you never liked is harmless.
    assert client.delete(
        f"/posts/{post['id']}/like", headers=bob["headers"]
    ).json()["likes_count"] == 0


def test_liking_requires_auth_and_a_real_post(client, alice, make_post):
    post = make_post(alice["headers"])
    assert client.post(f"/posts/{post['id']}/like").status_code == 401
    assert client.post("/posts/999/like", headers=alice["headers"]).status_code == 404


def test_timelines_report_the_viewers_like_state(client, alice, bob, make_post):
    post = make_post(alice["headers"])
    client.post(f"/posts/{post['id']}/like", headers=bob["headers"])

    anonymous = client.get("/posts/").json()["items"][0]
    assert anonymous["likes_count"] == 1
    assert anonymous["is_liked"] is False

    for_bob = client.get("/posts/", headers=bob["headers"]).json()["items"][0]
    assert for_bob["is_liked"] is True

    for_alice = client.get("/posts/feed", headers=alice["headers"]).json()["items"][0]
    assert for_alice["likes_count"] == 1
    assert for_alice["is_liked"] is False


def test_who_liked_a_post(client, alice, bob, make_post):
    post = make_post(alice["headers"])
    client.post(f"/posts/{post['id']}/like", headers=bob["headers"])

    likers = client.get(f"/posts/{post['id']}/likes", headers=alice["headers"]).json()
    assert likers["total"] == 1
    assert likers["items"][0]["username"] == "bob"


def test_liked_posts_timeline(client, alice, bob, make_post):
    post = make_post(alice["headers"], caption="a keeper")
    make_post(alice["headers"], caption="not for me")
    client.post(f"/posts/{post['id']}/like", headers=bob["headers"])

    liked = client.get("/posts/liked", headers=bob["headers"]).json()
    assert [item["caption"] for item in liked["items"]] == ["a keeper"]


def test_likes_disappear_with_the_post(client, alice, bob, make_post):
    post = make_post(alice["headers"])
    client.post(f"/posts/{post['id']}/like", headers=bob["headers"])
    client.delete(f"/posts/{post['id']}", headers=alice["headers"])

    assert client.get("/posts/liked", headers=bob["headers"]).json()["total"] == 0
