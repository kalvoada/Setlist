def test_register_returns_token_and_user(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "ada",
            "email": "Ada@Example.com",
            "password": "supersecret1",
            "display_name": "Ada L",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "ada"
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["followers_count"] == 0


def test_register_rejects_duplicate_username_case_insensitively(client, register):
    register("ada")
    response = client.post(
        "/auth/register",
        json={"username": "ADA", "email": "other@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 409


def test_register_rejects_duplicate_email(client, register):
    register("ada")
    response = client.post(
        "/auth/register",
        json={"username": "ada2", "email": "ada@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 409


def test_register_rejects_short_password_and_bad_username(client):
    weak = client.post(
        "/auth/register",
        json={"username": "ada", "email": "a@example.com", "password": "short"},
    )
    assert weak.status_code == 422

    bad_name = client.post(
        "/auth/register",
        json={"username": "a b", "email": "a@example.com", "password": "supersecret1"},
    )
    assert bad_name.status_code == 422


def test_login_with_username_or_email(client, register):
    register("ada")

    by_username = client.post(
        "/auth/login", json={"identifier": "ada", "password": "supersecret1"}
    )
    assert by_username.status_code == 200

    by_email = client.post(
        "/auth/login", json={"identifier": "ada@example.com", "password": "supersecret1"}
    )
    assert by_email.status_code == 200


def test_login_with_wrong_password_is_rejected(client, register):
    register("ada")
    response = client.post(
        "/auth/login", json={"identifier": "ada", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_me_requires_a_valid_token(client, alice):
    assert client.get("/users/me").status_code == 401
    assert client.get(
        "/users/me", headers={"Authorization": "Bearer nonsense"}
    ).status_code == 401

    response = client.get("/users/me", headers=alice["headers"])
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_refresh_returns_a_new_usable_token(client, alice):
    response = client.post("/auth/refresh", headers=alice["headers"])
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
