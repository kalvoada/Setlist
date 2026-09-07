"""Comments."""


def test_comment_lifecycle(client, alice, bob, make_post):
    post = make_post(alice["headers"])

    created = client.post(
        f"/posts/{post['id']}/comments",
        json={"content": "  this rips  "},
        headers=bob["headers"],
    )
    assert created.status_code == 201
    assert created.json()["content"] == "this rips"
    assert created.json()["author"]["username"] == "bob"

    listed = client.get(f"/posts/{post['id']}/comments").json()
    assert listed["total"] == 1

    feed_post = client.get("/posts/").json()["items"][0]
    assert feed_post["comments_count"] == 1


def test_comments_require_auth_and_content(client, alice, make_post):
    post = make_post(alice["headers"])
    assert client.post(f"/posts/{post['id']}/comments", json={"content": "hi"}).status_code == 401
    assert client.post(
        f"/posts/{post['id']}/comments", json={"content": "   "}, headers=alice["headers"]
    ).status_code == 422


def test_commenting_on_a_missing_post_is_404(client, alice):
    assert client.post(
        "/posts/999/comments", json={"content": "hello"}, headers=alice["headers"]
    ).status_code == 404
    assert client.get("/posts/999/comments").status_code == 404


def test_comment_deletion_rules(client, alice, bob, register, make_post):
    carol = register("carol")
    post = make_post(alice["headers"])

    comment = client.post(
        f"/posts/{post['id']}/comments", json={"content": "mine"}, headers=bob["headers"]
    ).json()

    # A bystander cannot delete someone else's comment.
    assert client.delete(f"/comments/{comment['id']}", headers=carol["headers"]).status_code == 403
    # The comment's author can.
    assert client.delete(f"/comments/{comment['id']}", headers=bob["headers"]).status_code == 204

    # So can the owner of the post.
    other = client.post(
        f"/posts/{post['id']}/comments", json={"content": "spam"}, headers=carol["headers"]
    ).json()
    assert client.delete(f"/comments/{other['id']}", headers=alice["headers"]).status_code == 204
    assert client.get(f"/posts/{post['id']}/comments").json()["total"] == 0
