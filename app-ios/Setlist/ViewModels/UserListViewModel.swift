import Foundation
import Observation

/// Where a list of people comes from.
enum UserListSource: Equatable, Identifiable {
    case followers(userId: Int)
    case following(userId: Int)
    case likes(postId: Int)

    var id: String {
        switch self {
        case let .followers(userId): return "followers-\(userId)"
        case let .following(userId): return "following-\(userId)"
        case let .likes(postId): return "likes-\(postId)"
        }
    }

    var title: String {
        switch self {
        case .followers: return "Followers"
        case .following: return "Following"
        case .likes: return "Likes"
        }
    }

    var emptyMessage: String {
        switch self {
        case .followers: return "No followers yet."
        case .following: return "Not following anyone yet."
        case .likes: return "No likes yet."
        }
    }
}

/// Backs the follower, following and "liked by" lists — same shape, one screen.
@MainActor
@Observable
final class UserListViewModel {
    private let pageSize = 25

    let source: UserListSource
    private(set) var users: [User] = []
    private(set) var isLoading = false
    private(set) var hasMore = false
    var errorMessage: String?

    private var offset = 0

    init(source: UserListSource) {
        self.source = source
    }

    func load(using api: APIService) async {
        guard users.isEmpty else { return }
        isLoading = true
        do {
            let page = try await fetch(api: api, offset: 0)
            users = page.items
            offset = page.items.count
            hasMore = page.hasMore
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func loadMore(after user: User, using api: APIService) async {
        guard hasMore, !isLoading, user.id == users.last?.id else { return }
        do {
            let page = try await fetch(api: api, offset: offset)
            let known = Set(users.map(\.id))
            users.append(contentsOf: page.items.filter { !known.contains($0.id) })
            offset += page.items.count
            hasMore = page.hasMore
        } catch {
            hasMore = false
        }
    }

    func toggleFollow(_ user: User, using api: APIService) async {
        guard let index = users.firstIndex(where: { $0.id == user.id }) else { return }
        let wasFollowing = users[index].isFollowing

        users[index].isFollowing.toggle()
        users[index].followersCount += users[index].isFollowing ? 1 : -1

        do {
            let state = wasFollowing
                ? try await api.unfollow(userId: user.id)
                : try await api.follow(userId: user.id)
            if let current = users.firstIndex(where: { $0.id == state.userId }) {
                users[current].isFollowing = state.isFollowing
                users[current].followersCount = state.followersCount
            }
        } catch {
            if let current = users.firstIndex(where: { $0.id == user.id }) {
                users[current].isFollowing = wasFollowing
                users[current].followersCount += wasFollowing ? 1 : -1
            }
            errorMessage = error.localizedDescription
        }
    }

    private func fetch(api: APIService, offset: Int) async throws -> Page<User> {
        switch source {
        case let .followers(userId):
            return try await api.followers(userId: userId, limit: pageSize, offset: offset)
        case let .following(userId):
            return try await api.following(userId: userId, limit: pageSize, offset: offset)
        case let .likes(postId):
            return try await api.likers(postId: postId, limit: pageSize, offset: offset)
        }
    }
}
