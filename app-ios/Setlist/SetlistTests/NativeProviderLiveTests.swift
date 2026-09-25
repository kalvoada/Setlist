import XCTest
@testable import Setlist

// End to end against the real services: the local backend (the app's
// SetlistAPIBaseURL), song.link and Apple's iTunes Search. Skipped when no
// backend is running, so the rest of the suite stays offline.
//
// The backend caches each lookup on the music item, so only the first run
// against a database actually calls song.link.
final class NativeProviderLiveTests: XCTestCase {

    private static let password = "supersecret1"

    @MainActor
    func testComeTogetherFromAppleMusicOpensOnSpotify() async throws {
        let api = try await signUpThrowawayUser()
        let apple = try await appleMusicLink(song: "Come Together", artist: "The Beatles", album: "Abbey Road")

        _ = try await api.updateNativeProvider("spotify")
        let post = try await api.createPost(musicUrl: apple.absoluteString, caption: "", preview: nil)
        let native = try await api.nativeLink(musicId: post.music.id)

        XCTAssertEqual(native.status, .resolved, "no verified Spotify match for \(apple)")
        let spotify = try XCTUnwrap(native.url.flatMap(URL.init(string:)))
        XCTAssertEqual(spotify.host, "open.spotify.com")
        XCTAssertTrue(spotify.path.hasPrefix("/track/"), "expected a Spotify track, got \(spotify)")

        var music = post.music
        music.native = native
        XCTAssertEqual(music.listenAction(nativeProvider: "spotify"), .open(spotify, service: "Spotify"))
    }

    // MARK: - Helpers

    // A fresh account, deleted again (with its posts) when the test ends.
    @MainActor
    private func signUpThrowawayUser() async throws -> APIService {
        let api = APIService()
        let username = "live_\(Int.random(in: 100_000...999_999))"

        let auth: AuthResponse
        do {
            auth = try await api.register(
                username: username,
                email: "\(username)@example.com",
                password: Self.password,
                displayName: nil
            )
        } catch APIError.transport(let reason) {
            throw XCTSkip("No backend running at \(APIService.defaultBaseURL): \(reason)")
        }

        api.accessToken = auth.accessToken
        addTeardownBlock { @MainActor in
            try? await api.deleteAccount(currentPassword: Self.password)
        }
        return api
    }

    private struct ITunesSearch: Decodable {
        struct Song: Decodable {
            let artistName: String
            let collectionName: String?
            let trackName: String
            let trackViewUrl: URL
        }

        let results: [Song]
    }

    // A real Apple Music link for the studio recording, rather than a hard-coded
    // catalogue id that could be wrong or change.
    private func appleMusicLink(song: String, artist: String, album: String) async throws -> URL {
        var components = URLComponents(string: "https://itunes.apple.com/search")!
        components.queryItems = [
            URLQueryItem(name: "term", value: "\(song) \(artist)"),
            URLQueryItem(name: "entity", value: "song"),
            URLQueryItem(name: "country", value: "us"),
            URLQueryItem(name: "limit", value: "50")
        ]
        let (data, _) = try await URLSession.shared.data(from: XCTUnwrap(components.url))
        let results = try JSONDecoder().decode(ITunesSearch.self, from: data).results

        let match = results.first {
            $0.artistName == artist
                && ($0.collectionName ?? "").hasPrefix(album)
                && ($0.trackName == song || $0.trackName.hasPrefix(song) && $0.trackName.contains("Remaster"))
        }
        return try XCTUnwrap(match?.trackViewUrl, "iTunes has no \(song) by \(artist) on \(album)")
    }
}
