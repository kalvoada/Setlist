import Foundation
import Observation

/// Debounced user search, with follow suggestions as the resting state.
@MainActor
@Observable
final class SearchViewModel {
    private(set) var results: [User] = []
    private(set) var suggestions: [User] = []
    private(set) var isSearching = false
    private(set) var hasSearched = false
    var errorMessage: String?

    private var searchTask: Task<Void, Never>?

    func loadSuggestions(using api: APIService, force: Bool = false) async {
        guard force || suggestions.isEmpty else { return }
        if let users = try? await api.suggestedUsers(limit: 15) {
            suggestions = users
        }
    }

    /// Waits for a pause in typing so we do not fire a request per keystroke.
    func search(query: String, using api: APIService) {
        searchTask?.cancel()

        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            results = []
            hasSearched = false
            isSearching = false
            return
        }

        searchTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled, let self else { return }

            self.isSearching = true
            do {
                let page = try await api.searchUsers(query: trimmed)
                guard !Task.isCancelled else { return }
                self.results = page.items
                self.errorMessage = nil
            } catch {
                guard !Task.isCancelled else { return }
                self.errorMessage = error.localizedDescription
            }
            self.isSearching = false
            self.hasSearched = true
        }
    }

    func clear() {
        searchTask?.cancel()
        results = []
        hasSearched = false
        isSearching = false
    }

    func toggleFollow(_ user: User, using api: APIService) async {
        let wasFollowing = user.isFollowing
        apply(userId: user.id) { row in
            row.isFollowing.toggle()
            row.followersCount += row.isFollowing ? 1 : -1
        }

        do {
            let state = wasFollowing
                ? try await api.unfollow(userId: user.id)
                : try await api.follow(userId: user.id)
            apply(userId: user.id) { row in
                row.isFollowing = state.isFollowing
                row.followersCount = state.followersCount
            }
        } catch {
            apply(userId: user.id) { row in
                row.isFollowing = wasFollowing
                row.followersCount += wasFollowing ? 1 : -1
            }
            errorMessage = error.localizedDescription
        }
    }

    private func apply(userId: Int, _ change: (inout User) -> Void) {
        if let index = results.firstIndex(where: { $0.id == userId }) {
            change(&results[index])
        }
        if let index = suggestions.firstIndex(where: { $0.id == userId }) {
            change(&suggestions[index])
        }
    }
}
