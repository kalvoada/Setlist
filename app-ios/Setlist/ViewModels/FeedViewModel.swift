import Foundation
import Observation

/// Drives the two home timelines and keeps like state in sync with the server.
@MainActor
@Observable
final class FeedViewModel {
    enum Scope: String, CaseIterable, Identifiable {
        case following
        case discover

        var id: String { rawValue }

        var title: String {
            switch self {
            case .following: return "Following"
            case .discover: return "Discover"
            }
        }
    }

    private let pageSize = 20

    var scope: Scope = .following
    private(set) var posts: [Post] = []
    private(set) var isLoading = false
    private(set) var isLoadingMore = false
    private(set) var hasLoadedOnce = false
    private(set) var hasMore = false
    var errorMessage: String?

    private var offset = 0

    var isEmpty: Bool { posts.isEmpty && !isLoading }

    // MARK: - Loading

    func load(using api: APIService) async {
        if isLoading { return }
        isLoading = true
        errorMessage = nil

        do {
            let page = try await fetch(api: api, offset: 0)
            posts = page.items
            offset = page.items.count
            hasMore = page.hasMore
        } catch is CancellationError {
            // The view went away; nothing to report.
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
        hasLoadedOnce = true
    }

    func loadMore(after post: Post, using api: APIService) async {
        guard hasMore, !isLoadingMore, !isLoading else { return }
        guard post.id == posts.last?.id else { return }

        isLoadingMore = true
        do {
            let page = try await fetch(api: api, offset: offset)
            let known = Set(posts.map(\.id))
            posts.append(contentsOf: page.items.filter { !known.contains($0.id) })
            offset += page.items.count
            hasMore = page.hasMore
        } catch {
            // A failed "load more" should not replace what is already on screen.
            hasMore = false
        }
        isLoadingMore = false
    }

    private func fetch(api: APIService, offset: Int) async throws -> Page<Post> {
        switch scope {
        case .following:
            return try await api.feed(limit: pageSize, offset: offset)
        case .discover:
            return try await api.discover(limit: pageSize, offset: offset)
        }
    }

    // MARK: - Mutations

    func insert(_ post: Post) {
        posts.insert(post, at: 0)
        offset += 1
    }

    func replace(_ post: Post) {
        guard let index = posts.firstIndex(where: { $0.id == post.id }) else { return }
        posts[index] = post
    }

    func remove(postId: Int) {
        posts.removeAll { $0.id == postId }
        offset = max(0, offset - 1)
    }

    /// Flips the heart immediately and reconciles with the server's count.
    func toggleLike(_ post: Post, using api: APIService) async {
        guard let index = posts.firstIndex(where: { $0.id == post.id }) else { return }

        let original = posts[index]
        posts[index].isLiked.toggle()
        posts[index].likesCount += posts[index].isLiked ? 1 : -1

        do {
            let state = original.isLiked
                ? try await api.unlike(postId: original.id)
                : try await api.like(postId: original.id)
            if let current = posts.firstIndex(where: { $0.id == state.postId }) {
                posts[current].isLiked = state.isLiked
                posts[current].likesCount = state.likesCount
            }
        } catch {
            if let current = posts.firstIndex(where: { $0.id == original.id }) {
                posts[current] = original
            }
            errorMessage = error.localizedDescription
        }
    }
}
