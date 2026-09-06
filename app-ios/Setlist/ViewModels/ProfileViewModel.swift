import Foundation
import Observation

/// A profile screen: the user, their posts and the follow button's state.
@MainActor
@Observable
final class ProfileViewModel {
    private let pageSize = 20

    private(set) var user: User?
    private(set) var posts: [Post] = []
    private(set) var isLoading = false
    private(set) var isLoadingMore = false
    private(set) var isUpdatingFollow = false
    private(set) var hasMore = false
    var errorMessage: String?

    private var offset = 0

    func load(userId: Int, using api: APIService) async {
        isLoading = true
        errorMessage = nil

        do {
            async let profile = api.user(id: userId)
            async let page = api.userPosts(id: userId, limit: pageSize, offset: 0)

            user = try await profile
            let loaded = try await page
            posts = loaded.items
            offset = loaded.items.count
            hasMore = loaded.hasMore
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func loadMore(after post: Post, using api: APIService) async {
        guard let user, hasMore, !isLoadingMore, post.id == posts.last?.id else { return }

        isLoadingMore = true
        do {
            let page = try await api.userPosts(id: user.id, limit: pageSize, offset: offset)
            let known = Set(posts.map(\.id))
            posts.append(contentsOf: page.items.filter { !known.contains($0.id) })
            offset += page.items.count
            hasMore = page.hasMore
        } catch {
            hasMore = false
        }
        isLoadingMore = false
    }

    func toggleFollow(using api: APIService) async {
        guard var user, !user.isMe, !isUpdatingFollow else { return }

        isUpdatingFollow = true
        let wasFollowing = user.isFollowing

        // Optimistic, so the button never feels laggy.
        user.isFollowing.toggle()
        user.followersCount += user.isFollowing ? 1 : -1
        self.user = user

        do {
            let state = wasFollowing
                ? try await api.unfollow(userId: user.id)
                : try await api.follow(userId: user.id)
            user.isFollowing = state.isFollowing
            user.followersCount = state.followersCount
            self.user = user
        } catch {
            user.isFollowing = wasFollowing
            user.followersCount += wasFollowing ? 1 : -1
            self.user = user
            errorMessage = error.localizedDescription
        }
        isUpdatingFollow = false
    }

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
        }
    }

    func remove(postId: Int) {
        posts.removeAll { $0.id == postId }
        if var user {
            user.postsCount = max(0, user.postsCount - 1)
            self.user = user
        }
    }

    func apply(_ user: User) {
        self.user = user
    }
}
