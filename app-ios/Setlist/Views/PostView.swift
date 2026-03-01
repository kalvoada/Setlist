import SwiftUI

// TODO
// username
// Likes
// Share
// Content: Spotify/AppleMusic - Songs/Albums/Playlists

// MARK: - PostRowStyle
// Controls how a PostRow renders in different contexts (feed, profile, compact)
struct PostRowStyle {
    var avatarSize: CGFloat = 30
    var showContent: Bool = true
    var font: Font = .body

    static let feed    = PostRowStyle(avatarSize: 30)
    static let profile = PostRowStyle(avatarSize: 20, font: .caption)
    static let compact = PostRowStyle(avatarSize: 16, showContent: false)
}

// MARK: - PostRow
// Reusable list row for a post
struct PostRow: View {
    let post: Post
    var style: PostRowStyle = .feed
    
    var body: some View {
        NavigationLink(destination: PostDetailView(post: post)) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "person.circle.fill")
                        .resizable()
                        .frame(width: style.avatarSize, height: style.avatarSize)
                        .foregroundColor(.athenaColorDarkBlue)
                        .clipShape(Circle())
                    Text("User \(post.user_id)") // TODO: get the user name
                        .font(.headline)
                        .foregroundColor(Color.athenaColorPink)
                }
                Text(post.content)
                    .font(.body)
            }
            
            .padding(.vertical, 8)
        }
    }
}

// MARK: - PostDetailView
// Full post screen with comment thread and inline comment composer
struct PostDetailView: View {
    let post: Post

    @StateObject private var apiService = APIService()
    @State private var comments: [Comment] = []
    @State private var newCommentText = ""
    @State private var isSubmitting = false

    let currentUserId = 1 //TODO: get the actual id

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {

            // ── Post content ──────────────────────────────────
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "person.circle.fill")
                        .resizable()
                        .frame(width: 40, height: 40)
                        .foregroundColor(.athenaColorDarkBlue)
                    Text("User \(post.user_id)")
                        .font(.headline)
                        .foregroundColor(.athenaColorPink)
                }
                Text(post.content)
                    .font(.body)
            }
            .padding()

            Divider()

            // ── Comments list ─────────────────────────────────
            List(comments) { comment in
                VStack(alignment: .leading, spacing: 4) {
                    Text("User \(comment.user_id)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(comment.content)
                        .font(.body)
                }
            }
            .listStyle(.plain)

            Divider()

            // ── Add comment bar ───────────────────────────────
            HStack {
                TextField("Add a comment...", text: $newCommentText)
                    .textFieldStyle(.roundedBorder)

                Button {
                    Task { await submitComment() }
                } label: {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Image(systemName: "paperplane.fill")
                            .foregroundColor(.athenaColorPink)
                    }
                }
                .disabled(newCommentText.trimmingCharacters(in: .whitespaces).isEmpty || isSubmitting)
            }
            .padding()
        }
        .navigationTitle("Post")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await loadComments()
        }
    }

    func loadComments() async {
        do {
            comments = try await apiService.fetchComments(postId: post.id)
        } catch {
            print("Error loading comments: \(error)")
        }
    }

    func submitComment() async {
        let text = newCommentText.trimmingCharacters(in: .whitespaces)
        guard !text.isEmpty else { return }

        isSubmitting = true
        do {
            let newComment = try await apiService.createComment(
                postId: post.id,
                content: text,
                userId: currentUserId
            )
            comments.append(newComment)
            newCommentText = ""
        } catch {
            print("Error posting comment: \(error)")
        }
        isSubmitting = false
    }
}

