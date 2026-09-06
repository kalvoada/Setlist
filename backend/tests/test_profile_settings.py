"""Profile edits, account settings and account deletion."""


def test_update_profile_fields(client, alice):
    response = client.patch(
        "/users/me",
        json={"display_name": "Alice A", "bio": "Only listens to shoegaze"},
        headers=alice["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["display_name"] == "Alice A"
    assert body["bio"] == "Only listens to shoegaze"

    # Partial updates leave other fields untouched.
    response = client.patch(
        "/users/me", json={"avatar_url": "https://cdn.example.com/a.jpg"},
        headers=alice["headers"],
    )
    assert response.json()["display_name"] == "Alice A"
    assert response.json()["avatar_url"] == "https://cdn.example.com/a.jpg"


def test_update_profile_requires_auth(client):
    assert client.patch("/users/me", json={"bio": "hi"}).status_code == 401


def test_bio_length_is_validated(client, alice):
    response = client.patch(
        "/users/me", json={"bio": "x" * 301}, headers=alice["headers"]
    )
    assert response.status_code == 422


def test_change_username_and_email(client, alice):
    response = client.patch(
        "/users/me/account",
        json={
            "current_password": alice["password"],
            "username": "alice_music",
            "email": "alice.music@example.com",
        },
        headers=alice["headers"],
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice_music"
    assert response.json()["email"] == "alice.music@example.com"


def test_account_changes_require_the_current_password(client, alice):
    response = client.patch(
        "/users/me/account",
        json={"current_password": "not-the-password", "username": "hacked"},
        headers=alice["headers"],
    )
    assert response.status_code == 403
    assert client.get("/users/me", headers=alice["headers"]).json()["username"] == "alice"


def test_username_conflicts_are_rejected(client, alice, bob):
    response = client.patch(
        "/users/me/account",
        json={"current_password": alice["password"], "username": "bob"},
        headers=alice["headers"],
    )
    assert response.status_code == 409


def test_change_password_invalidates_the_old_one(client, alice):
    response = client.patch(
        "/users/me/account",
        json={"current_password": alice["password"], "new_password": "brand-new-pass"},
        headers=alice["headers"],
    )
    assert response.status_code == 200

    old = client.post(
        "/auth/login", json={"identifier": "alice", "password": alice["password"]}
    )
    assert old.status_code == 401

    new = client.post(
        "/auth/login", json={"identifier": "alice", "password": "brand-new-pass"}
    )
    assert new.status_code == 200


def test_new_password_must_be_strong_enough(client, alice):
    response = client.patch(
        "/users/me/account",
        json={"current_password": alice["password"], "new_password": "short"},
        headers=alice["headers"],
    )
    assert response.status_code == 422


def test_delete_account_removes_the_user_and_their_posts(client, alice, bob, make_post):
    post = make_post(alice["headers"])
    client.post(f"/users/{alice['user']['id']}/follow", headers=bob["headers"])

    wrong = client.request(
        "DELETE",
        "/users/me",
        json={"current_password": "nope"},
        headers=alice["headers"],
    )
    assert wrong.status_code == 403

    response = client.request(
        "DELETE",
        "/users/me",
        json={"current_password": alice["password"]},
        headers=alice["headers"],
    )
    assert response.status_code == 204

    assert client.get("/users/me", headers=alice["headers"]).status_code == 401
    assert client.get(f"/posts/{post['id']}").status_code == 404
    assert client.get(f"/users/{alice['user']['id']}").status_code == 404
    assert client.get("/users/me", headers=bob["headers"]).json()["following_count"] == 0
