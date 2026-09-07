import SwiftUI

/// `UserListView` presented modally, with its own navigation stack so tapping
/// somebody opens their profile inside the sheet.
struct UserListSheet: View {
    let source: UserListSource

    @State private var path = NavigationPath()

    init(source: UserListSource) {
        self.source = source
    }

    var body: some View {
        NavigationStack(path: $path) {
            UserListView(source: source) { user in
                path.append(user)
            }
            .navigationDestination(for: User.self) { user in
                UserProfileView(userId: user.id, path: $path)
            }
        }
    }
}

/// Followers, following and "liked by" — one list, three sources.
struct UserListView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model: UserListViewModel

    let onOpenUser: (User) -> Void

    init(source: UserListSource, onOpenUser: @escaping (User) -> Void) {
        _model = State(initialValue: UserListViewModel(source: source))
        self.onOpenUser = onOpenUser
    }

    var body: some View {
        Group {
            if model.isLoading && model.users.isEmpty {
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if model.users.isEmpty {
                EmptyStateView(symbol: "person.2", title: model.source.emptyMessage)
            } else {
                List {
                    ForEach(model.users) { user in
                        UserRow(
                            user: user,
                            isMe: session.isCurrentUser(user),
                            onOpen: { onOpenUser(user) },
                            onToggleFollow: {
                                Task {
                                    await model.toggleFollow(user, using: session.api)
                                    // Your own "Following" counter just moved.
                                    await session.reloadCurrentUser()
                                }
                            }
                        )
                        .task { await model.loadMore(after: user, using: session.api) }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle(model.source.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("Done") { dismiss() }
            }
        }
        .task { await model.load(using: session.api) }
    }
}

/// A user in any list: avatar, name, bio and a follow button.
struct UserRow: View {
    let user: User
    var isMe: Bool = false
    var onOpen: () -> Void
    var onToggleFollow: (() -> Void)? = nil

    var body: some View {
        HStack(spacing: 12) {
            Button(action: onOpen) {
                HStack(spacing: 12) {
                    AvatarView(user: user, size: 44)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(user.name)
                            .font(.subheadline.weight(.semibold))
                        Text(user.handle)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if !user.bio.isEmpty {
                            Text(user.bio)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }

                    Spacer()
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            if !isMe, !user.isMe, let onToggleFollow {
                FollowButton(
                    isFollowing: user.isFollowing,
                    isCompact: true,
                    action: onToggleFollow
                )
            }
        }
        .padding(.vertical, 4)
    }
}
