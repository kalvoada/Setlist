import XCTest
@testable import Setlist

/// View-model behaviour that the UI depends on: optimistic updates, rollbacks
/// and the rules that keep a post from being created without music.
final class FeedViewModelTests: XCTestCase {

    @MainActor
    private func makeModel(
        stub: @escaping (URLRequest) throws -> (Data, URLResponse)
    ) -> (FeedViewModel, APIService) {
        let session = MockURLSession()
        session.handler = stub
        let service = APIService(
            baseURL: URL(string: "https://api.test")!,
            session: session,
            accessToken: "token"
        )
        return (FeedViewModel(), service)
    }

    @MainActor
    private func respond(_ json: String, status: Int = 200) -> (URLRequest) throws -> (Data, URLResponse) {
        { request in
            let response = HTTPURLResponse(
                url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil
            )!
            return (Data(json.utf8), response)
        }
    }

    @MainActor
    func testLoadFillsTheTimeline() async {
        let (model, service) = makeModel(stub: respond(Fixtures.page(Fixtures.post, total: 1)))

        await model.load(using: service)

        XCTAssertEqual(model.posts.count, 1)
        XCTAssertFalse(model.isLoading)
        XCTAssertTrue(model.hasLoadedOnce)
        XCTAssertNil(model.errorMessage)
    }

    @MainActor
    func testFailedLoadSurfacesAMessageAndNoPosts() async {
        let (model, service) = makeModel(
            stub: respond(#"{"detail": "boom"}"#, status: 500)
        )

        await model.load(using: service)

        XCTAssertTrue(model.posts.isEmpty)
        XCTAssertNotNil(model.errorMessage)
    }

    @MainActor
    func testLikeIsOptimisticAndReconcilesWithTheServer() async throws {
        let (model, service) = makeModel(stub: respond(Fixtures.page(Fixtures.post)))
        await model.load(using: service)

        let post = try XCTUnwrap(model.posts.first)
        XCTAssertTrue(post.isLiked)
        XCTAssertEqual(post.likesCount, 4)

        // Unliking: the server reports the authoritative count.
        let session = MockURLSession()
        session.handler = respond(#"{"post_id": 10, "is_liked": false, "likes_count": 3}"#)
        let unlikeService = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )

        await model.toggleLike(post, using: unlikeService)

        XCTAssertEqual(session.lastRequest?.httpMethod, "DELETE")
        XCTAssertFalse(model.posts[0].isLiked)
        XCTAssertEqual(model.posts[0].likesCount, 3)
    }

    @MainActor
    func testFailedLikeRollsBack() async throws {
        let (model, service) = makeModel(stub: respond(Fixtures.page(Fixtures.post)))
        await model.load(using: service)
        let post = try XCTUnwrap(model.posts.first)

        let session = MockURLSession()
        session.handler = respond(#"{"detail": "nope"}"#, status: 500)
        let failing = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )

        await model.toggleLike(post, using: failing)

        XCTAssertEqual(model.posts[0].isLiked, post.isLiked)
        XCTAssertEqual(model.posts[0].likesCount, post.likesCount)
        XCTAssertNotNil(model.errorMessage)
    }

    @MainActor
    func testInsertPutsANewPostOnTop() async {
        let (model, service) = makeModel(stub: respond(Fixtures.page(Fixtures.post)))
        await model.load(using: service)

        let fresh = Post(
            id: 99,
            caption: "brand new",
            createdAt: .now,
            author: User(id: 1, username: "alice"),
            music: MusicItem(
                id: 1,
                provider: "spotify",
                providerName: "Spotify",
                itemType: "track",
                url: "https://open.spotify.com/track/x",
                title: "New"
            )
        )
        model.insert(fresh)

        XCTAssertEqual(model.posts.first?.id, 99)
        XCTAssertEqual(model.posts.count, 2)

        model.remove(postId: 99)
        XCTAssertEqual(model.posts.count, 1)
    }
}

final class ComposePostViewModelTests: XCTestCase {

    @MainActor
    private func makeService(
        _ json: String, status: Int = 200
    ) -> (APIService, MockURLSession) {
        let session = MockURLSession()
        session.stub(json, status: status)
        let service = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )
        return (service, session)
    }

    @MainActor
    func testCannotPostWithoutAResolvedLink() async {
        let model = ComposePostViewModel()
        let (service, _) = makeService(Fixtures.post, status: 201)

        XCTAssertFalse(model.canPost)
        let post = await model.submit(using: service)
        XCTAssertNil(post, "a post must carry music")
        XCTAssertNotNil(model.errorMessage)
    }

    @MainActor
    func testResolvingALinkEnablesPosting() async {
        let model = ComposePostViewModel()
        let (service, _) = makeService("""
        { "provider": "spotify", "provider_name": "Spotify", "item_type": "track",
          "url": "https://open.spotify.com/track/abc", "title": "Weird Fishes",
          "artist_name": "Radiohead", "artwork_url": null, "preview_url": null }
        """)

        model.link = "https://open.spotify.com/track/abc"
        await model.resolve(using: service)

        XCTAssertEqual(model.preview?.title, "Weird Fishes")
        XCTAssertTrue(model.canPost)

        // Editing the link invalidates the preview again.
        model.link = "https://open.spotify.com/track/other"
        XCTAssertNil(model.preview)
        XCTAssertFalse(model.canPost)
    }

    @MainActor
    func testUnsupportedLinkReportsTheServerMessage() async {
        let model = ComposePostViewModel()
        let (service, _) = makeService(
            #"{"detail": "Link must be a song, album or playlist"}"#, status: 422
        )

        model.link = "https://example.com/cat.jpg"
        await model.resolve(using: service)

        XCTAssertNil(model.preview)
        XCTAssertEqual(model.errorMessage, "Link must be a song, album or playlist")
    }
}

final class AccountSettingsViewModelTests: XCTestCase {

    @MainActor
    private func model(for user: User) -> AccountSettingsViewModel {
        let model = AccountSettingsViewModel()
        model.start(from: user)
        return model
    }

    private var alice: User {
        User(id: 1, username: "alice", email: "alice@example.com")
    }

    @MainActor
    func testNoChangesMeansNothingToSave() {
        let model = model(for: alice)
        XCTAssertFalse(model.hasChanges)
        XCTAssertFalse(model.canSave)
    }

    @MainActor
    func testSavingRequiresTheCurrentPassword() {
        let model = model(for: alice)
        model.username = "alice_music"

        XCTAssertTrue(model.hasChanges)
        XCTAssertFalse(model.canSave, "the current password is still missing")

        model.currentPassword = "supersecret1"
        XCTAssertTrue(model.canSave)
    }

    @MainActor
    func testValidationMirrorsTheServerRules() {
        let model = model(for: alice)
        model.currentPassword = "supersecret1"

        model.username = "no spaces allowed"
        XCTAssertNotNil(model.validationMessage)

        model.username = "alice"
        model.email = "not-an-email"
        XCTAssertNotNil(model.validationMessage)

        model.email = "alice@example.com"
        model.newPassword = "short"
        XCTAssertNotNil(model.validationMessage)

        model.newPassword = "long-enough-password"
        model.confirmPassword = "different"
        XCTAssertEqual(model.validationMessage, "The new passwords do not match.")

        model.confirmPassword = "long-enough-password"
        XCTAssertNil(model.validationMessage)
        XCTAssertTrue(model.canSave)
    }
}

/// Following someone has to move two counters: the other person's follower
/// count, and — via the session — your own following count.
final class ProfileViewModelTests: XCTestCase {

    private static let profile = """
    {
      "id": 5, "username": "bob", "display_name": "Bob", "avatar_url": null,
      "bio": "", "followers_count": 3, "following_count": 1, "posts_count": 0,
      "is_following": false, "is_followed_by": false, "is_me": false,
      "created_at": "2026-01-02T03:04:05Z"
    }
    """

    /// Answers `/users/5` and `/users/5/posts` differently — the two calls
    /// `ProfileViewModel.load` makes concurrently.
    @MainActor
    private func makeService() -> (APIService, MockURLSession) {
        let session = MockURLSession()
        session.handler = { request in
            let path = request.url?.path ?? ""
            let body = path.hasSuffix("/posts")
                ? #"{"items": [], "limit": 20, "offset": 0, "total": 0, "has_more": false}"#
                : ProfileViewModelTests.profile
            let response = HTTPURLResponse(
                url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil
            )!
            return (Data(body.utf8), response)
        }
        let service = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )
        return (service, session)
    }

    @MainActor
    private func stub(_ session: MockURLSession, _ json: String, status: Int = 200) {
        session.handler = { request in
            let response = HTTPURLResponse(
                url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil
            )!
            return (Data(json.utf8), response)
        }
    }

    @MainActor
    func testLoadFetchesProfileAndPosts() async {
        let (service, _) = makeService()
        let model = ProfileViewModel()

        await model.load(userId: 5, using: service)

        XCTAssertEqual(model.user?.username, "bob")
        XCTAssertEqual(model.user?.followersCount, 3)
        XCTAssertFalse(model.user?.isFollowing ?? true)
        XCTAssertTrue(model.posts.isEmpty)
    }

    @MainActor
    func testFollowingRaisesTheFollowerCountAndKeepsTheServersNumber() async {
        let (service, session) = makeService()
        let model = ProfileViewModel()
        await model.load(userId: 5, using: service)

        // The server knows about a follower we hadn't seen yet: 3 + us + them.
        stub(session, #"{"user_id": 5, "is_following": true, "followers_count": 5}"#)
        await model.toggleFollow(using: service)

        XCTAssertTrue(model.user?.isFollowing ?? false)
        XCTAssertEqual(model.user?.followersCount, 5, "the server's count wins")
        XCTAssertEqual(session.lastRequest?.httpMethod, "POST")
        XCTAssertFalse(model.isUpdatingFollow)
    }

    @MainActor
    func testUnfollowUsesDelete() async {
        let (service, session) = makeService()
        let model = ProfileViewModel()
        await model.load(userId: 5, using: service)

        stub(session, #"{"user_id": 5, "is_following": true, "followers_count": 4}"#)
        await model.toggleFollow(using: service)

        stub(session, #"{"user_id": 5, "is_following": false, "followers_count": 3}"#)
        await model.toggleFollow(using: service)

        XCTAssertEqual(session.lastRequest?.httpMethod, "DELETE")
        XCTAssertFalse(model.user?.isFollowing ?? true)
        XCTAssertEqual(model.user?.followersCount, 3)
    }

    @MainActor
    func testFailedFollowRollsBackTheCounter() async {
        let (service, session) = makeService()
        let model = ProfileViewModel()
        await model.load(userId: 5, using: service)

        stub(session, #"{"detail": "nope"}"#, status: 500)
        await model.toggleFollow(using: service)

        XCTAssertFalse(model.user?.isFollowing ?? true)
        XCTAssertEqual(model.user?.followersCount, 3)
        XCTAssertNotNil(model.errorMessage)
    }
}

final class SearchViewModelFollowTests: XCTestCase {

    @MainActor
    private func makeService(_ json: String, status: Int = 200) -> (APIService, MockURLSession) {
        let session = MockURLSession()
        session.stub(json, status: status)
        let service = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )
        return (service, session)
    }

    @MainActor
    func testFollowingASuggestionUpdatesThatRow() async throws {
        let (service, session) = makeService("""
        [{ "id": 7, "username": "nora", "display_name": null, "avatar_url": null,
           "bio": "", "followers_count": 2, "following_count": 0, "posts_count": 0,
           "is_following": false, "is_followed_by": false, "is_me": false }]
        """)
        let model = SearchViewModel()

        await model.loadSuggestions(using: service)
        XCTAssertEqual(model.suggestions.count, 1)
        let user = try XCTUnwrap(model.suggestions.first)

        session.stub(#"{"user_id": 7, "is_following": true, "followers_count": 3}"#)
        await model.toggleFollow(user, using: service)

        XCTAssertTrue(model.suggestions[0].isFollowing)
        XCTAssertEqual(model.suggestions[0].followersCount, 3)
    }
}
