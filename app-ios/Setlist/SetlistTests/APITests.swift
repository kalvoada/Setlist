import XCTest
@testable import Setlist

// MARK: - Test doubles

/// Records the requests the client makes and replays canned responses.
final class MockURLSession: URLSessionProtocol {
    var handler: ((URLRequest) throws -> (Data, URLResponse))?
    private(set) var requests: [URLRequest] = []

    var lastRequest: URLRequest? { requests.last }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)
        guard let handler else {
            throw XCTSkip("No handler configured for \(request.url?.absoluteString ?? "?")")
        }
        return try handler(request)
    }

    /// Replies with `json` and the given status for every request.
    func stub(_ json: String, status: Int = 200) {
        handler = { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: status,
                httpVersion: nil,
                headerFields: nil
            )!
            return (Data(json.utf8), response)
        }
    }
}

enum Fixtures {
    static let user = """
    {
      "id": 1,
      "username": "alice",
      "display_name": "Alice",
      "avatar_url": null,
      "bio": "shoegaze",
      "followers_count": 3,
      "following_count": 2,
      "posts_count": 5,
      "is_following": true,
      "is_followed_by": false,
      "is_me": false,
      "created_at": "2026-01-02T03:04:05.123456Z",
      "email": "alice@example.com"
    }
    """

    /// The compact author shape embedded in posts — no counters at all.
    static let compactAuthor = """
    { "id": 2, "username": "bob", "display_name": null, "avatar_url": null, "bio": "" }
    """

    static let post = """
    {
      "id": 10,
      "caption": "on repeat",
      "created_at": "2026-02-03T10:11:12Z",
      "author": \(compactAuthor),
      "music": {
        "id": 7,
        "provider": "spotify",
        "provider_name": "Spotify",
        "item_type": "track",
        "url": "https://open.spotify.com/track/abc",
        "title": "Weird Fishes",
        "artist_name": "Radiohead",
        "artwork_url": null,
        "preview_url": null
      },
      "likes_count": 4,
      "comments_count": 1,
      "is_liked": true
    }
    """

    static func page(_ item: String, total: Int = 1, hasMore: Bool = false) -> String {
        """
        { "items": [\(item)], "limit": 20, "offset": 0, "total": \(total),
          "has_more": \(hasMore) }
        """
    }
}

// MARK: - APIService

final class APIServiceTests: XCTestCase {

    @MainActor
    private func makeService(
        token: String? = nil
    ) -> (APIService, MockURLSession) {
        let session = MockURLSession()
        let service = APIService(
            baseURL: URL(string: "https://api.test")!,
            session: session,
            accessToken: token
        )
        return (service, session)
    }

    // MARK: Decoding

    @MainActor
    func testFeedDecodesPostsAndSnakeCaseFields() async throws {
        let (service, session) = makeService(token: "token")
        session.stub(Fixtures.page(Fixtures.post, total: 42, hasMore: true))

        let page = try await service.feed()

        XCTAssertEqual(page.total, 42)
        XCTAssertTrue(page.hasMore)

        let post = try XCTUnwrap(page.items.first)
        XCTAssertEqual(post.id, 10)
        XCTAssertEqual(post.caption, "on repeat")
        XCTAssertEqual(post.likesCount, 4)
        XCTAssertEqual(post.commentsCount, 1)
        XCTAssertTrue(post.isLiked)
        XCTAssertEqual(post.music.title, "Weird Fishes")
        XCTAssertEqual(post.music.artistName, "Radiohead")
        XCTAssertEqual(post.music.subtitle, "Song · Spotify")
    }

    @MainActor
    func testCompactAuthorDecodesWithDefaults() async throws {
        let (service, session) = makeService(token: "token")
        session.stub(Fixtures.page(Fixtures.post))

        let page = try await service.feed()
        let post = try XCTUnwrap(page.items.first)

        // The embedded author carries no counters; they must default, not throw.
        XCTAssertEqual(post.author.username, "bob")
        XCTAssertEqual(post.author.followersCount, 0)
        XCTAssertFalse(post.author.isFollowing)
        XCTAssertEqual(post.author.name, "bob", "falls back to the username")
        XCTAssertEqual(post.author.handle, "@bob")
    }

    @MainActor
    func testCurrentUserDecodesCountersAndEmail() async throws {
        let (service, session) = makeService(token: "token")
        session.stub(Fixtures.user)

        let user = try await service.currentUser()

        XCTAssertEqual(user.email, "alice@example.com")
        XCTAssertEqual(user.followersCount, 3)
        XCTAssertEqual(user.followingCount, 2)
        XCTAssertEqual(user.postsCount, 5)
        XCTAssertTrue(user.isFollowing)
        XCTAssertNotNil(user.createdAt)
    }

    func testDatesParseWithAndWithoutFractionalSeconds() {
        XCTAssertNotNil(APIService.date(from: "2026-02-03T10:11:12Z"))
        XCTAssertNotNil(APIService.date(from: "2026-02-03T10:11:12.123456Z"))
        XCTAssertNil(APIService.date(from: "not a date"))
    }

    // MARK: Requests

    @MainActor
    func testAuthenticatedRequestsCarryTheBearerToken() async throws {
        let (service, session) = makeService(token: "abc123")
        session.stub(Fixtures.page(Fixtures.post))

        _ = try await service.feed()

        XCTAssertEqual(
            session.lastRequest?.value(forHTTPHeaderField: "Authorization"),
            "Bearer abc123"
        )
    }

    @MainActor
    func testSignInDoesNotSendAToken() async throws {
        let (service, session) = makeService()
        session.stub("""
        { "access_token": "t", "token_type": "bearer", "expires_in": 60,
          "user": \(Fixtures.user) }
        """)

        let response = try await service.login(identifier: "alice", password: "secret")

        XCTAssertEqual(response.accessToken, "t")
        XCTAssertEqual(response.user.username, "alice")
        XCTAssertNil(session.lastRequest?.value(forHTTPHeaderField: "Authorization"))
    }

    @MainActor
    func testPaginationParametersAreSentAsQueryItems() async throws {
        let (service, session) = makeService(token: "t")
        session.stub(Fixtures.page(Fixtures.post))

        _ = try await service.discover(limit: 5, offset: 10)

        let url = try XCTUnwrap(session.lastRequest?.url)
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        XCTAssertEqual(url.path, "/posts/", "the trailing slash must survive")
        XCTAssertEqual(items.first(where: { $0.name == "limit" })?.value, "5")
        XCTAssertEqual(items.first(where: { $0.name == "offset" })?.value, "10")
    }

    @MainActor
    func testCreatePostEncodesSnakeCaseBody() async throws {
        let (service, session) = makeService(token: "t")
        session.stub(Fixtures.post, status: 201)

        let preview = MusicLinkPreview(
            provider: "spotify",
            providerName: "Spotify",
            itemType: "track",
            url: "https://open.spotify.com/track/abc",
            title: "Weird Fishes",
            artistName: "Radiohead",
            artworkUrl: nil,
            previewUrl: nil
        )
        _ = try await service.createPost(
            musicUrl: preview.url,
            caption: "listen",
            preview: preview
        )

        let request = try XCTUnwrap(session.lastRequest)
        XCTAssertEqual(request.httpMethod, "POST")
        let body = try XCTUnwrap(request.httpBody)
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: body) as? [String: Any]
        )
        XCTAssertEqual(json["music_url"] as? String, "https://open.spotify.com/track/abc")
        XCTAssertEqual(json["caption"] as? String, "listen")
        XCTAssertEqual(json["artist_name"] as? String, "Radiohead")
    }

    @MainActor
    func testLikeUsesPostAndUnlikeUsesDelete() async throws {
        let (service, session) = makeService(token: "t")
        session.stub("""
        { "post_id": 10, "is_liked": true, "likes_count": 5 }
        """)

        let liked = try await service.like(postId: 10)
        XCTAssertEqual(session.lastRequest?.httpMethod, "POST")
        XCTAssertEqual(liked.likesCount, 5)
        XCTAssertTrue(liked.isLiked)

        session.stub("""
        { "post_id": 10, "is_liked": false, "likes_count": 4 }
        """)
        let unliked = try await service.unlike(postId: 10)
        XCTAssertEqual(session.lastRequest?.httpMethod, "DELETE")
        XCTAssertFalse(unliked.isLiked)
    }

    @MainActor
    func testFollowStateDecodes() async throws {
        let (service, session) = makeService(token: "t")
        session.stub("""
        { "user_id": 2, "is_following": true, "followers_count": 9 }
        """)

        let state = try await service.follow(userId: 2)

        XCTAssertEqual(state.userId, 2)
        XCTAssertTrue(state.isFollowing)
        XCTAssertEqual(state.followersCount, 9)
    }

    // MARK: Errors

    @MainActor
    func testUnauthorizedSignalsTheSession() async {
        let (service, session) = makeService(token: "stale")
        session.stub(#"{"detail": "Could not validate credentials"}"#, status: 401)

        var signedOut = false
        service.onUnauthorized = { signedOut = true }

        do {
            _ = try await service.currentUser()
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .unauthorized)
        }
        XCTAssertTrue(signedOut, "the session should be told to sign out")
    }

    @MainActor
    func testConflictSurfacesTheServerMessage() async {
        let (service, session) = makeService()
        session.stub(#"{"detail": "Username is already taken"}"#, status: 409)

        do {
            _ = try await service.register(
                username: "alice", email: "a@b.co", password: "supersecret1", displayName: nil
            )
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .conflict("Username is already taken"))
            XCTAssertEqual(error.localizedDescription, "Username is already taken")
        }
    }

    @MainActor
    func testValidationErrorListIsFlattenedIntoOneMessage() async {
        let (service, session) = makeService(token: "t")
        session.stub(
            """
            {"detail": [
              {"loc": ["body", "music_url"], "msg": "Field required", "type": "missing"}
            ]}
            """,
            status: 422
        )

        do {
            _ = try await service.createPost(musicUrl: "", caption: "", preview: nil)
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(
                error.localizedDescription,
                "Music url: Field required"
            )
        }
    }

    @MainActor
    func testMalformedJSONIsReportedAsInvalidData() async {
        let (service, session) = makeService(token: "t")
        session.stub("not json at all")

        do {
            _ = try await service.currentUser()
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .invalidData)
        }
    }

    @MainActor
    func testOfflineTransportErrorIsMapped() async {
        let (service, session) = makeService(token: "t")
        session.handler = { _ in throw URLError(.notConnectedToInternet) }

        do {
            _ = try await service.currentUser()
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .offline)
        }
    }
}
