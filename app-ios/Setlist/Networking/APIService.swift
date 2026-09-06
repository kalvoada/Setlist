import Foundation

// MARK: - URLSession abstraction for testability
// Lets unit tests inject a stub instead of making real network calls.
protocol URLSessionProtocol {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: URLSessionProtocol {}

// MARK: - APIService
/// The single place that knows how to talk to the Setlist backend.
///
/// Every call is `async`, returns decoded models and throws `APIError`, so
/// views and view models never touch `URLRequest` or status codes.
@MainActor
final class APIService {
    /// Overridable from the generated Info.plist (`SetlistAPIBaseURL`) so the
    /// same build can point at a local server or a deployed one.
    nonisolated static var defaultBaseURL: URL {
        if let configured = Bundle.main.object(forInfoDictionaryKey: "SetlistAPIBaseURL") as? String,
           !configured.isEmpty,
           let url = URL(string: configured) {
            return url
        }
        return URL(string: "http://127.0.0.1:8000")!
    }

    private let baseURL: URL
    private let session: URLSessionProtocol
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    /// Bearer token attached to authenticated requests.
    var accessToken: String?
    /// Called when the server rejects our token, so the app can sign out.
    var onUnauthorized: (@MainActor () -> Void)?

    init(
        baseURL: URL = APIService.defaultBaseURL,
        session: URLSessionProtocol = URLSession.shared,
        accessToken: String? = nil
    ) {
        self.baseURL = baseURL
        self.session = session
        self.accessToken = accessToken

        decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            guard let date = APIService.date(from: text) else {
                throw DecodingError.dataCorrupted(
                    DecodingError.Context(
                        codingPath: decoder.codingPath,
                        debugDescription: "Unrecognised date: \(text)"
                    )
                )
            }
            return date
        }

        encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    /// The API sends ISO-8601 UTC, with or without fractional seconds.
    nonisolated static func date(from text: String) -> Date? {
        let withFraction = ISO8601DateFormatter()
        withFraction.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = withFraction.date(from: text) { return date }

        let plain = ISO8601DateFormatter()
        plain.formatOptions = [.withInternetDateTime]
        return plain.date(from: text)
    }

    // MARK: - Auth

    func register(
        username: String,
        email: String,
        password: String,
        displayName: String?
    ) async throws -> AuthResponse {
        try await send(
            "/auth/register",
            method: .post,
            body: RegisterRequest(
                username: username,
                email: email,
                password: password,
                displayName: displayName
            ),
            authenticated: false
        )
    }

    func login(identifier: String, password: String) async throws -> AuthResponse {
        try await send(
            "/auth/login",
            method: .post,
            body: LoginRequest(identifier: identifier, password: password),
            authenticated: false
        )
    }

    /// Swaps a still-valid token for a fresh one; used on app launch.
    func refreshSession() async throws -> AuthResponse {
        try await send("/auth/refresh", method: .post)
    }

    func currentUser() async throws -> User {
        try await send("/users/me")
    }

    // MARK: - Profile & account settings

    func updateProfile(
        displayName: String?,
        bio: String?,
        avatarUrl: String?
    ) async throws -> User {
        try await send(
            "/users/me",
            method: .patch,
            body: ProfileUpdateRequest(
                displayName: displayName,
                bio: bio,
                avatarUrl: avatarUrl
            )
        )
    }

    func updateAccount(
        currentPassword: String,
        username: String? = nil,
        email: String? = nil,
        newPassword: String? = nil
    ) async throws -> User {
        try await send(
            "/users/me/account",
            method: .patch,
            body: AccountUpdateRequest(
                currentPassword: currentPassword,
                username: username,
                email: email,
                newPassword: newPassword
            )
        )
    }

    func deleteAccount(currentPassword: String) async throws {
        try await sendIgnoringResponse(
            "/users/me",
            method: .delete,
            body: AccountDeleteRequest(currentPassword: currentPassword)
        )
    }

    // MARK: - Users

    func user(id: Int) async throws -> User {
        try await send("/users/\(id)")
    }

    func userPosts(id: Int, limit: Int = 20, offset: Int = 0) async throws -> Page<Post> {
        try await send("/users/\(id)/posts", query: Self.pageQuery(limit, offset))
    }

    func searchUsers(query: String, limit: Int = 25, offset: Int = 0) async throws -> Page<User> {
        var items = Self.pageQuery(limit, offset)
        items.append(URLQueryItem(name: "q", value: query))
        return try await send("/users/search", query: items)
    }

    func suggestedUsers(limit: Int = 10) async throws -> [User] {
        try await send("/users/suggested", query: [URLQueryItem(name: "limit", value: "\(limit)")])
    }

    func followers(userId: Int, limit: Int = 25, offset: Int = 0) async throws -> Page<User> {
        try await send("/users/\(userId)/followers", query: Self.pageQuery(limit, offset))
    }

    func following(userId: Int, limit: Int = 25, offset: Int = 0) async throws -> Page<User> {
        try await send("/users/\(userId)/following", query: Self.pageQuery(limit, offset))
    }

    func follow(userId: Int) async throws -> FollowState {
        try await send("/users/\(userId)/follow", method: .post)
    }

    func unfollow(userId: Int) async throws -> FollowState {
        try await send("/users/\(userId)/follow", method: .delete)
    }

    // MARK: - Posts

    /// Posts from the people you follow, plus your own.
    func feed(limit: Int = 20, offset: Int = 0) async throws -> Page<Post> {
        try await send("/posts/feed", query: Self.pageQuery(limit, offset))
    }

    /// Everything on Setlist, newest first.
    func discover(limit: Int = 20, offset: Int = 0) async throws -> Page<Post> {
        try await send("/posts/", query: Self.pageQuery(limit, offset))
    }

    func likedPosts(limit: Int = 20, offset: Int = 0) async throws -> Page<Post> {
        try await send("/posts/liked", query: Self.pageQuery(limit, offset))
    }

    func post(id: Int) async throws -> Post {
        try await send("/posts/\(id)")
    }

    /// Turns a pasted streaming link into a preview before posting it.
    func resolveMusicLink(_ url: String) async throws -> MusicLinkPreview {
        try await send("/posts/resolve-link", method: .post, body: ResolveLinkRequest(url: url))
    }

    func createPost(musicUrl: String, caption: String, preview: MusicLinkPreview?) async throws -> Post {
        try await send(
            "/posts/",
            method: .post,
            body: CreatePostRequest(
                musicUrl: musicUrl,
                caption: caption,
                title: preview?.title,
                artistName: preview?.artistName,
                artworkUrl: preview?.artworkUrl,
                previewUrl: preview?.previewUrl
            )
        )
    }

    func updatePost(id: Int, caption: String) async throws -> Post {
        try await send("/posts/\(id)", method: .patch, body: UpdatePostRequest(caption: caption))
    }

    func deletePost(id: Int) async throws {
        try await sendIgnoringResponse("/posts/\(id)", method: .delete)
    }

    // MARK: - Likes

    func like(postId: Int) async throws -> LikeState {
        try await send("/posts/\(postId)/like", method: .post)
    }

    func unlike(postId: Int) async throws -> LikeState {
        try await send("/posts/\(postId)/like", method: .delete)
    }

    func likers(postId: Int, limit: Int = 25, offset: Int = 0) async throws -> Page<User> {
        try await send("/posts/\(postId)/likes", query: Self.pageQuery(limit, offset))
    }

    // MARK: - Comments

    func comments(postId: Int, limit: Int = 50, offset: Int = 0) async throws -> Page<Comment> {
        try await send("/posts/\(postId)/comments", query: Self.pageQuery(limit, offset))
    }

    func createComment(postId: Int, content: String) async throws -> Comment {
        try await send(
            "/posts/\(postId)/comments",
            method: .post,
            body: CreateCommentRequest(content: content)
        )
    }

    func deleteComment(id: Int) async throws {
        try await sendIgnoringResponse("/comments/\(id)", method: .delete)
    }

    // MARK: - Request plumbing

    enum HTTPMethod: String {
        case get = "GET"
        case post = "POST"
        case patch = "PATCH"
        case delete = "DELETE"
    }

    private static func pageQuery(_ limit: Int, _ offset: Int) -> [URLQueryItem] {
        [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)")
        ]
    }

    private func send<Response: Decodable>(
        _ path: String,
        method: HTTPMethod = .get,
        query: [URLQueryItem] = [],
        body: (any Encodable)? = nil,
        authenticated: Bool = true
    ) async throws -> Response {
        let data = try await perform(path, method: method, query: query, body: body, authenticated: authenticated)
        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.invalidData
        }
    }

    private func sendIgnoringResponse(
        _ path: String,
        method: HTTPMethod,
        query: [URLQueryItem] = [],
        body: (any Encodable)? = nil,
        authenticated: Bool = true
    ) async throws {
        _ = try await perform(path, method: method, query: query, body: body, authenticated: authenticated)
    }

    private func perform(
        _ path: String,
        method: HTTPMethod,
        query: [URLQueryItem],
        body: (any Encodable)?,
        authenticated: Bool
    ) async throws -> Data {
        // Built by hand rather than with `appendingPathComponent` so trailing
        // slashes survive: FastAPI answers `/posts/` and redirects `/posts`.
        let root = baseURL.absoluteString.hasSuffix("/")
            ? String(baseURL.absoluteString.dropLast())
            : baseURL.absoluteString
        guard var components = URLComponents(string: root + path) else {
            throw APIError.invalidURL
        }
        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.invalidURL }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try? encoder.encode(body)
        }
        if authenticated, let accessToken, !accessToken.isEmpty {
            request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError {
            throw error.code == .notConnectedToInternet ? APIError.offline
                                                        : APIError.transport(error.localizedDescription)
        } catch {
            throw APIError.transport(error.localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }

        guard (200..<300).contains(http.statusCode) else {
            let message = (try? decoder.decode(APIErrorBody.self, from: data))?.detail
            let apiError = APIError.from(status: http.statusCode, message: message)
            if case .unauthorized = apiError { onUnauthorized?() }
            throw apiError
        }

        return data
    }
}
