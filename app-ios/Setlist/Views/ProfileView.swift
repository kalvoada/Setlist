import SwiftUI

// MARK: - ProfileView
/// The "you" tab.
struct ProfileView: View {
    @Environment(SessionStore.self) private var session
    @State private var isComposing = false
    @State private var path = NavigationPath()

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if let currentUser = session.currentUser {
                    ProfileScreen(userId: currentUser.id, path: $path)
                } else {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: Post.self) { post in
                PostDetailView(post: post, path: $path)
            }
            .navigationDestination(for: User.self) { user in
                UserProfileView(userId: user.id, path: $path)
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
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink {
                        SettingsView(path: $path)
                    } label: {
                        Image(systemName: "gearshape")
                            .foregroundStyle(Color.setlistAccent)
                    }
                    .accessibilityLabel("Settings")
                }
            }
            .sheet(isPresented: $isComposing) {
                ComposePostView { _ in
                    Task { await session.reloadCurrentUser() }
                }
            }
        }
    }
}

// MARK: - UserProfileView
/// Somebody else's profile, pushed onto an existing navigation stack.
struct UserProfileView: View {
    let userId: Int
    @Binding var path: NavigationPath

    var body: some View {
        ProfileScreen(userId: userId, path: $path)
            .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - ProfileScreen
/// Shared layout for every profile: header, counters, action, posts.
struct ProfileScreen: View {
    @Environment(SessionStore.self) private var session

    let userId: Int
    @Binding var path: NavigationPath

    @State private var model = ProfileViewModel()
    @State private var isEditing = false
    @State private var listSource: UserListSource?

    private var isMe: Bool { userId == session.currentUser?.id }

    /// For your own profile the session is the source of truth: following
    /// someone from Search or a follower list updates it, and this screen has
    /// to show the new counter without being reloaded by hand.
    private var user: User? {
        isMe ? (session.currentUser ?? model.user) : model.user
    }

    var body: some View {
        Group {
            if let user {
                List {
                    Section {
                        ProfileHeader(
                            user: user,
                            isMe: isMe,
                            isUpdatingFollow: model.isUpdatingFollow,
                            onEdit: { isEditing = true },
                            onToggleFollow: {
                                Task {
                                    await model.toggleFollow(using: session.api)
                                    await session.reloadCurrentUser()
                                }
                            },
                            onShowFollowers: { listSource = .followers(userId: user.id) },
                            onShowFollowing: { listSource = .following(userId: user.id) }
                        )
                        .listRowInsets(EdgeInsets(top: 12, leading: 16, bottom: 12, trailing: 16))
                        .listRowSeparator(.hidden)
                    }

                    Section {
                        if model.posts.isEmpty {
                            Text(isMe ? "You have not posted yet." : "No posts yet.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                                .listRowSeparator(.hidden)
                        } else {
                            ForEach(model.posts) { post in
                                PostRow(
                                    post: post,
                                    showsAuthor: !isMe,
                                    onOpenPost: { path.append(post) },
                                    onOpenAuthor: { path.append(post.author) },
                                    onLike: {
                                        Task { await model.toggleLike(post, using: session.api) }
                                    }
                                )
                                .task { await model.loadMore(after: post, using: session.api) }
                            }
                        }
                    } header: {
                        Text("Posts")
                    }
                }
                .listStyle(.plain)
                .refreshable { await model.load(userId: userId, using: session.api) }
            } else if model.isLoading {
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let error = model.errorMessage {
                ErrorStateView(message: error) {
                    Task { await model.load(userId: userId, using: session.api) }
                }
            } else {
                EmptyStateView(symbol: "person.slash", title: "Profile unavailable")
            }
        }
        .navigationTitle(user?.name ?? "Profile")
        .task {
            // Reloaded on every appearance so counters and posts are current
            // when you come back to the tab; the list stays on screen while it
            // refreshes, so there is no flicker.
            await model.load(userId: userId, using: session.api)
        }
        .sheet(isPresented: $isEditing) {
            EditProfileView { updated in
                model.apply(updated)
                session.apply(updated)
            }
        }
        .sheet(item: $listSource) { source in
            UserListSheet(source: source)
        }
    }
}

// MARK: - ProfileHeader
struct ProfileHeader: View {
    let user: User
    let isMe: Bool
    let isUpdatingFollow: Bool
    let onEdit: () -> Void
    let onToggleFollow: () -> Void
    let onShowFollowers: () -> Void
    let onShowFollowing: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            AvatarView(user: user, size: 92)

            VStack(spacing: 2) {
                Text(user.name)
                    .font(.title2.bold())
                Text(user.handle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if !user.bio.isEmpty {
                Text(user.bio)
                    .font(.subheadline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            HStack {
                StatView(value: user.postsCount, label: "Posts")

                Button(action: onShowFollowers) {
                    StatView(value: user.followersCount, label: "Followers")
                }
                .buttonStyle(.plain)

                Button(action: onShowFollowing) {
                    StatView(value: user.followingCount, label: "Following")
                }
                .buttonStyle(.plain)
            }
            .padding(.vertical, 4)

            if isMe {
                Button("Edit profile", action: onEdit)
                    .buttonStyle(.bordered)
                    .tint(.setlistAccent)
            } else {
                HStack(spacing: 8) {
                    FollowButton(
                        isFollowing: user.isFollowing,
                        isBusy: isUpdatingFollow,
                        action: onToggleFollow
                    )
                    if user.isFollowedBy {
                        Text("Follows you")
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.setlistSurface, in: Capsule())
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity)
    }
}
