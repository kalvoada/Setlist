import Foundation
import Observation

// Owns "who is signed in" for the whole app.
@MainActor
@Observable
final class SessionStore {
    enum Phase: Equatable {
        // Checking the Keychain on launch
        case restoring
        case signedOut
        case signedIn
    }

    private static let tokenAccount = "access-token"

    private(set) var phase: Phase = .restoring
    private(set) var currentUser: User?

    let api: APIService

    // Pass a client in from tests
    init(api: APIService? = nil) {
        let client = api ?? APIService()
        self.api = client
        client.onUnauthorized = { [weak self] in
            self?.signOut()
        }
    }

    var isSignedIn: Bool { phase == .signedIn }

    // MARK: - Lifecycle

    // Restores a stored session, refreshing the token so it does not go stale.
    func restore() async {
        guard let token = KeychainStore.read(Self.tokenAccount), !token.isEmpty else {
            phase = .signedOut
            return
        }

        api.accessToken = token
        do {
            let response = try await api.refreshSession()
            store(response)
        } catch APIError.unauthorized {
            signOut()
        } catch {
            // Offline or the server is down: keep the token and let the user in with what we know, rather than logging them out.
            do {
                currentUser = try await api.currentUser()
                phase = .signedIn
            } catch {
                signOut()
            }
        }
    }

    func signIn(identifier: String, password: String) async throws {
        store(try await api.login(identifier: identifier, password: password))
    }

    func register(
        username: String,
        email: String,
        password: String,
        displayName: String?
    ) async throws {
        store(
            try await api.register(
                username: username,
                email: email,
                password: password,
                displayName: displayName
            )
        )
    }

    func signOut() {
        KeychainStore.delete(Self.tokenAccount)
        api.accessToken = nil
        currentUser = nil
        phase = .signedOut
    }

    // MARK: - Current user

    // Pulls fresh counters after following someone, posting, and so on.
    func reloadCurrentUser() async {
        guard isSignedIn else { return }
        currentUser = try? await api.currentUser()
    }

    func apply(_ user: User) {
        currentUser = user
    }

    func isCurrentUser(_ user: User) -> Bool {
        user.id == currentUser?.id
    }

    private func store(_ response: AuthResponse) {
        KeychainStore.save(response.accessToken, for: Self.tokenAccount)
        api.accessToken = response.accessToken
        currentUser = response.user
        phase = .signedIn
    }
}
