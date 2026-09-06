"""The follow graph and how it shapes the feed."""


def test_follow_and_unfollow_updates_counts(client, alice, bob):
    bob_id = bob["user"]["id"]

    response = client.post(f"/users/{bob_id}/follow", headers=alice["headers"])
    assert response.status_code == 200
    assert response.json() == {"user_id": bob_id, "is_following": True, "followers_count": 1}

    # Following twice is a no-op rather than an error.
    again = client.post(f"/users/{bob_id}/follow", headers=alice["headers"])
    assert again.json()["followers_count"] == 1

    profile = client.get(f"/users/{bob_id}", headers=alice["headers"]).json()
    assert profile["followers_count"] == 1
    assert profile["is_following"] is True

    mine = client.get("/users/me", headers=alice["headers"]).json()
    assert mine["following_count"] == 1

    response = client.delete(f"/users/{bob_id}/follow", headers=alice["headers"])
    assert response.json() == {"user_id": bob_id, "is_following": False, "followers_count": 0}


def test_cannot_follow_yourself(client, alice):
    response = client.post(
        f"/users/{alice['user']['id']}/follow", headers=alice["headers"]
    )
    assert response.status_code == 400


def test_following_requires_auth_and_a_real_user(client, alice):
    assert client.post("/users/1/follow").status_code == 401
    assert client.post("/users/9999/follow", headers=alice["headers"]).status_code == 404


def test_follower_and_following_lists(client, alice, bob, register):
    carol = register("carol")
    bob_id = bob["user"]["id"]

    client.post(f"/users/{bob_id}/follow", headers=alice["headers"])
    client.post(f"/users/{bob_id}/follow", headers=carol["headers"])

    followers = client.get(f"/users/{bob_id}/followers", headers=bob["headers"]).json()
    assert followers["total"] == 2
    assert {user["username"] for user in followers["items"]} == {"alice", "carol"}
    # Bob does not follow them back yet, but they follow him.
    assert all(user["is_followed_by"] for user in followers["items"])
    assert not any(user["is_following"] for user in followers["items"])

    following = client.get(
        f"/users/{alice['user']['id']}/following", headers=alice["headers"]
    ).json()
    assert following["total"] == 1
    assert following["items"][0]["username"] == "bob"
    assert following["items"][0]["is_following"] is True


def test_feed_contains_followed_users_and_yourself(client, alice, bob, register, make_post):
    carol = register("carol")
    make_post(bob["headers"], caption="from bob")
    make_post(carol["headers"], caption="from carol")
    make_post(alice["headers"], caption="from alice")

    before = client.get("/posts/feed", headers=alice["headers"]).json()
    assert [post["caption"] for post in before["items"]] == ["from alice"]

    client.post(f"/users/{bob['user']['id']}/follow", headers=alice["headers"])

    after = client.get("/posts/feed", headers=alice["headers"]).json()
    assert {post["caption"] for post in after["items"]} == {"from alice", "from bob"}
    assert after["total"] == 2

    # Discover still shows everything.
    discover = client.get("/posts/").json()
    assert discover["total"] == 3


def test_feed_requires_auth(client):
    assert client.get("/posts/feed").status_code == 401


def test_suggested_users_excludes_self_and_followed(client, alice, bob, register):
    register("carol")
    client.post(f"/users/{bob['user']['id']}/follow", headers=alice["headers"])

    suggested = client.get("/users/suggested", headers=alice["headers"]).json()
    assert {user["username"] for user in suggested} == {"carol"}


def test_user_search_reports_follow_state(client, alice, bob):
    client.post(f"/users/{bob['user']['id']}/follow", headers=alice["headers"])

    results = client.get("/users/search", params={"q": "bo"}, headers=alice["headers"]).json()
    assert results["total"] == 1
    assert results["items"][0]["username"] == "bob"
    assert results["items"][0]["is_following"] is True
    assert results["items"][0]["followers_count"] == 1


def test_search_matches_display_name_case_insensitively(client, alice, register):
    register("xyz", display_name="Thom Yorke")
    results = client.get("/users/search", params={"q": "thom"}).json()
    assert results["items"][0]["username"] == "xyz"
