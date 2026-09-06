import SwiftUI

/// Followers, following and "liked by" — one list, three sources.
struct UserListView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model: UserListViewModel

    init(source: UserListViewModel.Source) {
        _model = State(initialValue: UserListViewModel(source: source))
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
                        UserRow(user: user, isMe: session.isCurrentUser(user)) {
                            Task { await model.toggleFollow(user, using: session.api) }
                        }
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
    var onToggleFollow: (() -> Void)? = nil

    var body: some View {
        HStack(spacing: 12) {
            NavigationLink(value: user) {
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
