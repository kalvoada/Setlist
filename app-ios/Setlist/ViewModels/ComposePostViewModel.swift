import Foundation
import Observation
import UIKit

/// Composing a post: paste a streaming link, check the preview, add a caption.
///
/// The link is resolved by the backend so the app shows exactly what will be
/// stored — and so a post can never be created without music attached.
@MainActor
@Observable
final class ComposePostViewModel {
    /// Editing the link invalidates whatever we resolved from the old one.
    var link: String = "" {
        didSet {
            guard link != resolvedLink else { return }
            preview = nil
            resolvedLink = nil
        }
    }

    var caption: String = ""
    private(set) var preview: MusicLinkPreview?
    private(set) var isResolving = false
    private(set) var isPosting = false
    var errorMessage: String?

    private var resolvedLink: String?

    var canPost: Bool { preview != nil && !isPosting }

    var trimmedLink: String {
        link.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Offers the clipboard when it holds something that looks like a link.
    func pasteFromClipboard() {
        guard let text = UIPasteboard.general.string?.trimmingCharacters(in: .whitespacesAndNewlines),
              text.contains("://") || text.hasPrefix("spotify:") else { return }
        link = text
    }

    func resolve(using api: APIService) async {
        let candidate = trimmedLink
        guard !candidate.isEmpty, candidate != resolvedLink else { return }

        isResolving = true
        errorMessage = nil
        preview = nil

        do {
            preview = try await api.resolveMusicLink(candidate)
            resolvedLink = candidate
        } catch {
            errorMessage = error.localizedDescription
            resolvedLink = nil
        }
        isResolving = false
    }

    func clearPreview() {
        preview = nil
        resolvedLink = nil
        errorMessage = nil
    }

    /// Creates the post and returns it so the feed can show it straight away.
    func submit(using api: APIService) async -> Post? {
        guard let preview else {
            errorMessage = "Add a song, album or playlist link first."
            return nil
        }

        isPosting = true
        errorMessage = nil
        defer { isPosting = false }

        do {
            return try await api.createPost(
                musicUrl: preview.url,
                caption: caption.trimmingCharacters(in: .whitespacesAndNewlines),
                preview: preview
            )
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}
