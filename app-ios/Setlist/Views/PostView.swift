import SwiftUI

// MARK: - PostRow
/// A post in a timeline: who shared it, what they said, and the music itself.
///
/// The header and the body are separate navigation links (author vs. post) and
/// the action bar sits outside both, so every tap target does one thing.
struct PostRow: View {
    let post: Post
    var showsAuthor: Bool = true
    var onLike: () -> Void
    var onOpenLikes: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: Metrics.rowSpacing) {
            if showsAuthor {
                NavigationLink(value: post.author) {
                    PostAuthorHeader(author: post.author, date: post.relativeDate)
                }
                .buttonStyle(.plain)
            }

            NavigationLink(value: post) {
                VStack(alignment: .leading, spacing: Metrics.rowSpacing) {
                    if !post.caption.isEmpty {
                        Text(post.caption)
                            .font(.body)
                            .foregroundStyle(.primary)
                            .multilineTextAlignment(.leading)
                    }
                    MusicCardView(music: post.music)
                }
            }
            .buttonStyle(.plain)

            HStack(spacing: 20) {
                LikeButton(isLiked: post.isLiked, count: post.likesCount, action: onLike)

                NavigationLink(value: post) {
                    Label(post.commentsCount.formatted(), systemImage: "bubble.right")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.borderless)

                if let onOpenLikes, post.likesCount > 0 {
                    Button("Who liked", action: onOpenLikes)
                        .font(.footnote)
                        .buttonStyle(.borderless)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if let link = post.music.link {
                    ShareLink(item: link) {
                        Image(systemName: "square.and.arrow.up")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.borderless)
                }
            }
            .padding(.top, 2)
        }
        .padding(.vertical, 8)
    }
}

/// Avatar + name + handle + timestamp.
struct PostAuthorHeader: View {
    let author: User
    let date: String

    var body: some View {
        HStack(spacing: 10) {
            AvatarView(user: author, size: 40)

            VStack(alignment: .leading, spacing: 1) {
                Text(author.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                Text(author.handle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text(date)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - PostDetailView
/// A single post with its comment thread and a composer pinned to the bottom.
struct PostDetailView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model: PostDetailViewModel
    @State private var showingLikes = false
    @State private var showingDeleteConfirmation = false

    /// Called when the post is deleted so the parent list can drop it.
    var onDelete: ((Int) -> Void)? = nil

    init(post: Post, onDelete: ((Int) -> Void)? = nil) {
        _model = State(initialValue: PostDetailViewModel(post: post))
        self.onDelete = onDelete
    }

    private var isAuthor: Bool {
        model.post.author.id == session.currentUser?.id
    }

    var body: some View {
        VStack(spacing: 0) {
            commentList
            Divider()
            composer
        }
        .navigationTitle("Post")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if isAuthor {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        Button(role: .destructive) {
                            showingDeleteConfirmation = true
                        } label: {
                            Label("Delete post", systemImage: "trash")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                            .foregroundStyle(Color.setlistAccent)
                    }
                }
            }
        }
        .confirmationDialog(
            "Delete this post?",
            isPresented: $showingDeleteConfirmation,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task {
                    if await model.deletePost(using: session.api) {
                        onDelete?(model.post.id)
                        dismiss()
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        }
        .sheet(isPresented: $showingLikes) {
            NavigationStack {
                UserListView(source: .likes(postId: model.post.id))
                    .navigationDestination(for: User.self) { user in
                        UserProfileView(userId: user.id)
                    }
            }
        }
        .task { await model.load(using: session.api) }
        .alert(
            "Something went wrong",
            isPresented: Binding(
                get: { model.errorMessage != nil },
                set: { if !$0 { model.errorMessage = nil } }
            )
        ) {
            Button("OK", role: .cancel) { model.errorMessage = nil }
        } message: {
            Text(model.errorMessage ?? "")
        }
    }

    private var commentList: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: Metrics.rowSpacing) {
                    NavigationLink(value: model.post.author) {
                        PostAuthorHeader(author: model.post.author, date: model.post.relativeDate)
                    }
                    .buttonStyle(.plain)

                    if !model.post.caption.isEmpty {
                        Text(model.post.caption).font(.body)
                    }

                    MusicCardView(music: model.post.music, artworkSize: 80)

                    HStack(spacing: 20) {
                        LikeButton(
                            isLiked: model.post.isLiked,
                            count: model.post.likesCount
                        ) {
                            Task { await model.toggleLike(using: session.api) }
                        }

                        if model.post.likesCount > 0 {
                            Button("Who liked") { showingLikes = true }
                                .font(.footnote)
                                .buttonStyle(.borderless)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        if let link = model.post.music.link {
                            ShareLink(item: link) {
                                Image(systemName: "square.and.arrow.up")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.borderless)
                        }
                    }
                }
                .listRowSeparator(.hidden)
            }

            Section("Comments") {
                if model.comments.isEmpty {
                    Text("No comments yet. Say something nice.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .listRowSeparator(.hidden)
                } else {
                    ForEach(model.comments) { comment in
                        CommentRow(comment: comment)
                            .swipeActions(edge: .trailing) {
                                if model.canDelete(comment, currentUserId: session.currentUser?.id) {
                                    Button("Delete", role: .destructive) {
                                        Task { await model.deleteComment(comment, using: session.api) }
                                    }
                                }
                            }
                    }
                }
            }
        }
        .listStyle(.plain)
        .refreshable { await model.load(using: session.api) }
    }

    private var composer: some View {
        HStack(spacing: 10) {
            TextField("Add a comment…", text: $model.draft, axis: .vertical)
                .lineLimit(1...4)
                .textFieldStyle(.roundedBorder)
                .submitLabel(.send)

            Button {
                Task { await model.submitComment(using: session.api) }
            } label: {
                if model.isSubmitting {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "paperplane.fill")
                        .foregroundStyle(model.canSubmit ? Color.setlistAccent : Color.secondary)
                }
            }
            .disabled(!model.canSubmit)
            .accessibilityLabel("Send comment")
        }
        .padding(.horizontal)
        .padding(.vertical, 8)
        .background(.bar)
    }
}

/// One comment in the thread.
struct CommentRow: View {
    let comment: Comment

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            NavigationLink(value: comment.author) {
                AvatarView(user: comment.author, size: 32)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(comment.author.name)
                        .font(.footnote.weight(.semibold))
                    Text(comment.relativeDate)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                Text(comment.content)
                    .font(.subheadline)
            }
        }
        .padding(.vertical, 2)
    }
}
