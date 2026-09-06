import SwiftUI

// MARK: - FeedView
/// The home tab: what the people you follow are listening to, or everything.
struct FeedView: View {
    @Environment(SessionStore.self) private var session

    @State private var model = FeedViewModel()
    @State private var isComposing = false

    var body: some View {
        NavigationStack {
            content
                .navigationBarTitleDisplayMode(.inline)
                .navigationDestination(for: Post.self) { post in
                    PostDetailView(post: post) { deletedId in
                        model.remove(postId: deletedId)
                    }
                }
                .navigationDestination(for: User.self) { user in
                    UserProfileView(userId: user.id)
                }
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            isComposing = true
                        } label: {
                            Image(systemName: "plus")
                                .fontWeight(.bold)
                                .foregroundStyle(Color.setlistAccent)
                        }
                        .accessibilityLabel("New post")
                    }

                    ToolbarItem(placement: .principal) {
                        Text("SETLIST")
                            .font(.headline)
                            .fontWeight(.bold)
                            .tracking(5)
                            .foregroundStyle(Color.setlistAccent)
                    }
                }
                .sheet(isPresented: $isComposing) {
                    ComposePostView { post in
                        model.insert(post)
                        Task { await session.reloadCurrentUser() }
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        VStack(spacing: 0) {
            Picker("Timeline", selection: Binding(
                get: { model.scope },
                set: { newScope in
                    guard newScope != model.scope else { return }
                    model.scope = newScope
                    Task { await model.load(using: session.api) }
                }
            )) {
                ForEach(FeedScope.allCases) { scope in
                    Text(scope.title).tag(scope)
                }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.bottom, 8)

            timeline
        }
        .task {
            if !model.hasLoadedOnce {
                await model.load(using: session.api)
            }
        }
    }

    @ViewBuilder
    private var timeline: some View {
        if model.isLoading && model.posts.isEmpty {
            ProgressView("Loading…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if let error = model.errorMessage, model.posts.isEmpty {
            ErrorStateView(message: error) {
                Task { await model.load(using: session.api) }
            }
        } else if model.posts.isEmpty {
            emptyState
        } else {
            List {
                ForEach(model.posts) { post in
                    PostRow(post: post) {
                        Task { await model.toggleLike(post, using: session.api) }
                    }
                    .listRowSeparator(.visible)
                    .task { await model.loadMore(after: post, using: session.api) }
                }

                if model.isLoadingMore {
                    LoadingFooter()
                }
            }
            .listStyle(.plain)
            .refreshable { await model.load(using: session.api) }
        }
    }

    private var emptyState: some View {
        Group {
            switch model.scope {
            case .following:
                EmptyStateView(
                    symbol: "person.2",
                    title: "Your feed is quiet",
                    message: "Follow a few people, or share the first song yourself.",
                    actionTitle: "Share a song"
                ) {
                    isComposing = true
                }
            case .discover:
                EmptyStateView(
                    symbol: "music.note",
                    title: "Nothing here yet",
                    message: "Be the first to post a song, album or playlist.",
                    actionTitle: "Share a song"
                ) {
                    isComposing = true
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
