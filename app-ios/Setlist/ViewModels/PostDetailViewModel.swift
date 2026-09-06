import Foundation
import Observation

/// One post with its comment thread.
@MainActor
@Observable
final class PostDetailViewModel {
    private(set) var post: Post
    private(set) var comments: [Comment] = []
    private(set) var isLoading = false
    private(set) var isSubmitting = false
    var draft: String = ""
    var errorMessage: String?

    init(post: Post) {
        self.post = post
        self.comments = post.comments ?? []
    }

    var canSubmit: Bool {
        !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isSubmitting
    }

    func load(using api: APIService) async {
        isLoading = true
        do {
            let fresh = try await api.post(id: post.id)
            post = fresh
            comments = fresh.comments ?? []
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    func toggleLike(using api: APIService) async {
        let wasLiked = post.isLiked
        post.isLiked.toggle()
        post.likesCount += post.isLiked ? 1 : -1

        do {
            let state = wasLiked
                ? try await api.unlike(postId: post.id)
                : try await api.like(postId: post.id)
            post.isLiked = state.isLiked
            post.likesCount = state.likesCount
        } catch {
            post.isLiked = wasLiked
            post.likesCount += wasLiked ? 1 : -1
            errorMessage = error.localizedDescription
        }
    }

    func submitComment(using api: APIService) async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        isSubmitting = true
        do {
            let comment = try await api.createComment(postId: post.id, content: text)
            comments.append(comment)
            post.commentsCount += 1
            draft = ""
        } catch {
            errorMessage = error.localizedDescription
        }
        isSubmitting = false
    }

    func deleteComment(_ comment: Comment, using api: APIService) async {
        do {
            try await api.deleteComment(id: comment.id)
            comments.removeAll { $0.id == comment.id }
            post.commentsCount = max(0, post.commentsCount - 1)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func deletePost(using api: APIService) async -> Bool {
        do {
            try await api.deletePost(id: post.id)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func canDelete(_ comment: Comment, currentUserId: Int?) -> Bool {
        guard let currentUserId else { return false }
        return comment.author.id == currentUserId || post.author.id == currentUserId
    }
}
