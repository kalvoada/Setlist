import XCTest
@testable import Setlist

// Opening shared music on the listener's own streaming service.
final class NativeProviderTests: XCTestCase {

    private static let spotifyURL = URL(string: "https://open.spotify.com/track/abc")!
    private static let appleURL = URL(string: "https://music.apple.com/us/album/weird-fishes/1109714933?i=1109715167")!

    private static func post(native: String) -> String {
        """
        {
          "id": 10, "caption": "", "created_at": "2026-02-03T10:11:12Z",
          "author": \(Fixtures.compactAuthor),
          "music": {
            "id": 7, "provider": "spotify", "provider_name": "Spotify",
            "item_type": "track", "url": "https://open.spotify.com/track/abc",
            "title": "Weird Fishes", "artist_name": "Radiohead",
            "artwork_url": null, "preview_url": null,
            "native": \(native)
          }
        }
        """
    }

    private func music(
        provider: String = "spotify",
        providerName: String = "Spotify",
        itemType: String = "track",
        url: String = spotifyURL.absoluteString,
        native: NativeLink? = nil
    ) -> MusicItem {
        MusicItem(
            id: 7,
            provider: provider,
            providerName: providerName,
            itemType: itemType,
            url: url,
            title: "Weird Fishes",
            native: native
        )
    }

    private func appleMusic(_ status: NativeLink.Status, url: String? = nil) -> NativeLink {
        NativeLink(status: status, provider: "apple_music", providerName: "Apple Music", url: url)
    }

    @MainActor
    private func makeService(_ json: String, status: Int = 200) -> (APIService, MockURLSession) {
        let session = MockURLSession()
        session.stub(json, status: status)
        let service = APIService(
            baseURL: URL(string: "https://api.test")!, session: session, accessToken: "t"
        )
        return (service, session)
    }

    // MARK: Decoding

    @MainActor
    func testFeedCarriesWhereEachSongOpensForTheListener() async throws {
        let (service, _) = makeService(Fixtures.page(Self.post(native: """
        { "status": "resolved", "provider": "apple_music", "provider_name": "Apple Music",
          "url": "\(Self.appleURL.absoluteString)" }
        """)))

        let page = try await service.feed()
        let music = try XCTUnwrap(page.items.first).music

        XCTAssertEqual(music.native?.status, .resolved)
        XCTAssertEqual(
            music.listenAction(nativeProvider: "apple_music"),
            .open(Self.appleURL, service: "Apple Music")
        )
    }

    @MainActor
    func testPostsWithoutANativeLinkDecodeAsBefore() async throws {
        let (service, _) = makeService(Fixtures.page(Fixtures.post))

        let page = try await service.feed()
        let music = try XCTUnwrap(page.items.first).music

        XCTAssertNil(music.native)
        XCTAssertEqual(
            music.listenAction(nativeProvider: nil),
            .open(Self.spotifyURL, service: "Spotify")
        )
    }

    @MainActor
    func testAStatusThisVersionDoesNotKnowIsLookedUp() async throws {
        let (service, _) = makeService(Fixtures.page(Self.post(native: """
        { "status": "something_new", "provider": "apple_music",
          "provider_name": "Apple Music", "url": null }
        """)))

        let page = try await service.feed()
        let music = try XCTUnwrap(page.items.first).music

        XCTAssertEqual(music.native?.status, .pending)
        XCTAssertEqual(music.listenAction(nativeProvider: "apple_music"), .lookUp)
    }

    @MainActor
    func testCurrentUserDecodesTheChosenService() async throws {
        let (service, _) = makeService("""
        { "id": 1, "username": "alice", "bio": "", "email": "alice@example.com",
          "native_provider": "apple_music" }
        """)

        let user = try await service.currentUser()

        XCTAssertEqual(user.nativeProvider, "apple_music")
    }

    // MARK: What play does

    func testWithoutAChosenServiceMusicOpensWhereItWasShared() {
        XCTAssertEqual(
            music(native: appleMusic(.resolved, url: Self.appleURL.absoluteString))
                .listenAction(nativeProvider: nil),
            .open(Self.spotifyURL, service: "Spotify")
        )
    }

    func testAMatchOpensOnTheListenersService() {
        XCTAssertEqual(
            music(native: appleMusic(.resolved, url: Self.appleURL.absoluteString))
                .listenAction(nativeProvider: "apple_music"),
            .open(Self.appleURL, service: "Apple Music")
        )
    }

    func testBandcampAndSoundCloudOpenOnTheirOwnLinks() {
        let bandcamp = "https://artist.bandcamp.com/track/some-song"
        XCTAssertEqual(
            music(provider: "bandcamp", providerName: "Bandcamp", url: bandcamp, native: appleMusic(.original))
                .listenAction(nativeProvider: "apple_music"),
            .open(URL(string: bandcamp)!, service: "Bandcamp")
        )

        let soundcloud = "https://soundcloud.com/artist/some-song"
        XCTAssertEqual(
            music(provider: "soundcloud", providerName: "SoundCloud", url: soundcloud, native: appleMusic(.original))
                .listenAction(nativeProvider: "apple_music"),
            .open(URL(string: soundcloud)!, service: "SoundCloud")
        )
    }

    func testNoMatchSaysSoInsteadOfOpeningSomethingElse() {
        XCTAssertEqual(
            music(native: appleMusic(.unavailable)).listenAction(nativeProvider: "apple_music"),
            .unavailable(service: "Apple Music")
        )
    }

    func testAMatchWithABrokenLinkIsNotOpened() {
        XCTAssertEqual(
            music(native: appleMusic(.resolved, url: "")).listenAction(nativeProvider: "apple_music"),
            .unavailable(service: "Apple Music")
        )
    }

    func testNotLookedUpYetAsksTheServer() {
        XCTAssertEqual(
            music(native: appleMusic(.pending)).listenAction(nativeProvider: "apple_music"),
            .lookUp
        )
        // The feed loaded before the listener picked a service.
        XCTAssertEqual(music().listenAction(nativeProvider: "apple_music"), .lookUp)
    }

    func testSwitchingServicesIgnoresTheOldAnswer() {
        XCTAssertEqual(
            music(native: appleMusic(.resolved, url: Self.appleURL.absoluteString))
                .listenAction(nativeProvider: "deezer"),
            .lookUp
        )
    }

    func testNothingToOpenHidesPlay() {
        XCTAssertNil(music(url: "").listenAction(nativeProvider: nil))
    }

    // MARK: Requests

    @MainActor
    func testLookingUpAsksForThatMusicItem() async throws {
        let (service, session) = makeService("""
        { "status": "resolved", "provider": "apple_music", "provider_name": "Apple Music",
          "url": "\(Self.appleURL.absoluteString)" }
        """)

        let native = try await service.nativeLink(musicId: 7)

        XCTAssertEqual(session.lastRequest?.httpMethod, "GET")
        XCTAssertEqual(session.lastRequest?.url?.absoluteString, "https://api.test/music/7/native-link")
        XCTAssertEqual(native.status, .resolved)
        XCTAssertEqual(native.url, Self.appleURL.absoluteString)
    }

    @MainActor
    func testAFailedLookupSurfacesTheServersMessage() async {
        let message = "Couldn't look this up on Apple Music right now. Try again in a moment."
        let (service, _) = makeService(#"{"detail": "\#(message)"}"#, status: 503)

        do {
            _ = try await service.nativeLink(musicId: 7)
            XCTFail("Expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .server(status: 503, message: message))
            XCTAssertEqual(error.localizedDescription, message)
        }
    }

    @MainActor
    func testChoosingAServiceSavesItOnTheAccount() async throws {
        let (service, session) = makeService("""
        { "id": 1, "username": "alice", "bio": "", "native_provider": "apple_music" }
        """)
        let store = SessionStore(api: service)

        try await store.setNativeProvider("apple_music")

        let request = try XCTUnwrap(session.lastRequest)
        XCTAssertEqual(request.httpMethod, "PATCH")
        XCTAssertEqual(request.url?.path, "/users/me")
        let data = try XCTUnwrap(request.httpBody)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: String])
        XCTAssertEqual(body, ["native_provider": "apple_music"], "other profile fields are left alone")
        XCTAssertEqual(store.currentUser?.nativeProvider, "apple_music")
    }

    @MainActor
    func testClearingTheServiceSendsAnEmptyValue() async throws {
        let (service, session) = makeService(#"{ "id": 1, "username": "alice", "bio": "" }"#)
        let store = SessionStore(api: service)

        try await store.setNativeProvider(nil)

        let data = try XCTUnwrap(session.lastRequest?.httpBody)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: String])
        XCTAssertEqual(body, ["native_provider": ""])
        XCTAssertNil(store.currentUser?.nativeProvider)
    }

    func testEveryServiceTheAPIKnowsCanBePicked() {
        XCTAssertEqual(
            MusicService.allCases.map(\.rawValue),
            ["spotify", "apple_music", "youtube_music", "tidal", "deezer", "soundcloud", "bandcamp"]
        )
    }
}
