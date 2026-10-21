import XCTest
@testable import Setlist

// Where shared music plays for the listener: their own service's player when
// it was matched there, the original's otherwise, and the plain card as the
// fallback.
final class NativeProviderTests: XCTestCase {

    private static let spotifyURL = URL(string: "https://open.spotify.com/track/abc")!
    private static let spotifyPlayer = URL(string: "https://open.spotify.com/embed/track/abc")!
    private static let appleURL = URL(string: "https://music.apple.com/us/album/weird-fishes/1109714933?i=1109715167")!
    private static let applePlayer = URL(string: "https://embed.music.apple.com/us/album/weird-fishes/1109714933?i=1109715167")!

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
            "embed_url": "\(spotifyPlayer.absoluteString)",
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
        embedUrl: String? = spotifyPlayer.absoluteString,
        native: NativeLink? = nil
    ) -> MusicItem {
        MusicItem(
            id: 7,
            provider: provider,
            providerName: providerName,
            itemType: itemType,
            url: url,
            title: "Weird Fishes",
            embedUrl: embedUrl,
            native: native
        )
    }

    private func appleMusic(
        _ status: NativeLink.Status,
        url: String? = nil,
        embedUrl: String? = nil
    ) -> NativeLink {
        NativeLink(
            status: status, provider: "apple_music", providerName: "Apple Music",
            url: url, embedUrl: embedUrl
        )
    }

    private var matchedOnAppleMusic: NativeLink {
        appleMusic(.resolved, url: Self.appleURL.absoluteString, embedUrl: Self.applePlayer.absoluteString)
    }

    private static let playsOnSpotify = MusicItem.ListenAction.open(.init(
        url: spotifyURL, service: "Spotify", provider: "spotify", player: spotifyPlayer
    ))

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
    func testFeedCarriesTheListenersPlayer() async throws {
        let (service, _) = makeService(Fixtures.page(Self.post(native: """
        { "status": "resolved", "provider": "apple_music", "provider_name": "Apple Music",
          "url": "\(Self.appleURL.absoluteString)",
          "embed_url": "\(Self.applePlayer.absoluteString)" }
        """)))

        let page = try await service.feed()
        let music = try XCTUnwrap(page.items.first).music

        XCTAssertEqual(music.native?.status, .resolved)
        XCTAssertEqual(
            music.listenAction(nativeProvider: "apple_music"),
            .open(.init(url: Self.appleURL, service: "Apple Music", provider: "apple_music",
                        player: Self.applePlayer))
        )
    }

    @MainActor
    func testPostsWithoutPlayersOrNativeLinksDecodeAsBefore() async throws {
        let (service, _) = makeService(Fixtures.page(Fixtures.post))

        let page = try await service.feed()
        let music = try XCTUnwrap(page.items.first).music

        XCTAssertNil(music.native)
        XCTAssertNil(music.embedUrl)
        XCTAssertEqual(
            music.listenAction(nativeProvider: nil),
            .open(.init(url: Self.spotifyURL, service: "Spotify", provider: "spotify", player: nil))
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
          "native_provider": "youtube_music" }
        """)

        let user = try await service.currentUser()

        XCTAssertEqual(user.nativeProvider, "youtube_music")
    }

    // MARK: Which player

    func testWithoutAChosenServiceTheOriginalPlayerShows() {
        XCTAssertEqual(
            music(native: matchedOnAppleMusic).listenAction(nativeProvider: nil),
            Self.playsOnSpotify
        )
    }

    func testAMatchPlaysInTheListenersService() {
        XCTAssertEqual(
            music(native: matchedOnAppleMusic).listenAction(nativeProvider: "apple_music"),
            .open(.init(url: Self.appleURL, service: "Apple Music", provider: "apple_music",
                        player: Self.applePlayer))
        )
    }

    func testMusicAlreadyOnTheListenersServicePlaysAsShared() {
        let native = NativeLink(
            status: .resolved, provider: "spotify", providerName: "Spotify",
            url: Self.spotifyURL.absoluteString, embedUrl: Self.spotifyPlayer.absoluteString
        )
        XCTAssertEqual(music(native: native).listenAction(nativeProvider: "spotify"), Self.playsOnSpotify)
    }

    func testBandcampAndSoundCloudPlayInTheirOwnPlayers() {
        let bandcamp = "https://artist.bandcamp.com/track/some-song"
        let bandcampPlayer = "https://bandcamp.com/EmbeddedPlayer/v=2/track=2436476419/size=large/"
        XCTAssertEqual(
            music(provider: "bandcamp", providerName: "Bandcamp", url: bandcamp,
                  embedUrl: bandcampPlayer, native: appleMusic(.original))
                .listenAction(nativeProvider: "apple_music"),
            .open(.init(url: URL(string: bandcamp)!, service: "Bandcamp", provider: "bandcamp",
                        player: URL(string: bandcampPlayer)!))
        )

        let soundcloud = "https://soundcloud.com/artist/some-song"
        let soundcloudPlayer = "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Fsome-song"
        XCTAssertEqual(
            music(provider: "soundcloud", providerName: "SoundCloud", url: soundcloud,
                  embedUrl: soundcloudPlayer, native: appleMusic(.original))
                .listenAction(nativeProvider: "apple_music"),
            .open(.init(url: URL(string: soundcloud)!, service: "SoundCloud", provider: "soundcloud",
                        player: URL(string: soundcloudPlayer)!))
        )
    }

    func testOnlyTheServicesOwnPlayersAreLoaded() {
        let native = appleMusic(.resolved, url: Self.appleURL.absoluteString,
                                embedUrl: "https://evil.example/player")
        guard case let .open(destination)? = music(native: native).listenAction(nativeProvider: "apple_music") else {
            return XCTFail("expected to open")
        }
        XCTAssertNil(destination.player, "falls back to the plain card")
        XCTAssertEqual(destination.url, Self.appleURL)

        let insecure = music(embedUrl: "http://open.spotify.com/embed/track/abc")
        guard case let .open(original)? = insecure.listenAction(nativeProvider: nil) else {
            return XCTFail("expected to open")
        }
        XCTAssertNil(original.player)
    }

    // MARK: Which look

    func testAServiceWithAPlayerShowsIt() {
        guard case let .open(destination)? = music(native: matchedOnAppleMusic)
            .listenAction(nativeProvider: "apple_music")
        else { return XCTFail("expected to open") }
        XCTAssertEqual(destination.look, .player(Self.applePlayer))
    }

    func testYouTubeMusicGetsItsOwnCard() {
        let native = NativeLink(
            status: .resolved, provider: "youtube_music", providerName: "YouTube Music",
            url: "https://music.youtube.com/watch?v=Hj6rYAOtV8E", embedUrl: nil
        )
        guard case let .open(destination)? = music(native: native)
            .listenAction(nativeProvider: "youtube_music")
        else { return XCTFail("expected to open") }
        XCTAssertEqual(destination.look, .youTubeMusic)
        XCTAssertEqual(destination.url.absoluteString, "https://music.youtube.com/watch?v=Hj6rYAOtV8E")
    }

    func testAServiceWithoutAPlayerFallsBackToTheCard() {
        // A Bandcamp post whose page gave no player id.
        let bandcamp = music(
            provider: "bandcamp", providerName: "Bandcamp",
            url: "https://artist.bandcamp.com/track/some-song", embedUrl: nil
        )
        guard case let .open(destination)? = bandcamp.listenAction(nativeProvider: nil) else {
            return XCTFail("expected to open")
        }
        XCTAssertEqual(destination.look, .card)
    }

    func testNoMatchSaysSoInsteadOfPlayingSomethingElse() {
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
            music(native: matchedOnAppleMusic).listenAction(nativeProvider: "youtube_music"),
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

    func testOnlyServicesMusicCanBeMatchedIntoArePicked() {
        XCTAssertEqual(
            MusicService.allCases.map(\.rawValue), ["spotify", "apple_music", "youtube_music"]
        )
    }
}
