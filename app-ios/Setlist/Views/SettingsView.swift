import SwiftUI

/// Settings hub: profile, account, and the way out.
struct SettingsView: View {
    @Environment(SessionStore.self) private var session

    @Binding var path: NavigationPath

    @State private var isEditingProfile = false
    @State private var showingSignOutConfirmation = false

    var body: some View {
        List {
            if let user = session.currentUser {
                Section {
                    HStack(spacing: 12) {
                        AvatarView(user: user, size: 52)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(user.name).font(.headline)
                            Text(user.handle)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }

            Section("Profile") {
                Button {
                    isEditingProfile = true
                } label: {
                    Label("Edit profile", systemImage: "person.crop.circle")
                }

                NavigationLink {
                    AccountSettingsView()
                } label: {
                    Label("Account", systemImage: "lock")
                }
            }

            Section("Activity") {
                NavigationLink {
                    LikedPostsView(path: $path)
                } label: {
                    Label("Posts you liked", systemImage: "heart")
                }
            }

            Section("About") {
                LabeledContent("Version", value: Bundle.main.appVersion)
                Link(destination: URL(string: "https://github.com/kalvoada/Setlist")!) {
                    Label("Source code", systemImage: "chevron.left.forwardslash.chevron.right")
                }
            }

            Section {
                Button(role: .destructive) {
                    showingSignOutConfirmation = true
                } label: {
                    Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                }
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $isEditingProfile) {
            EditProfileView { updated in
                session.apply(updated)
            }
        }
        .confirmationDialog(
            "Sign out of Setlist?",
            isPresented: $showingSignOutConfirmation,
            titleVisibility: .visible
        ) {
            Button("Sign out", role: .destructive) { session.signOut() }
            Button("Cancel", role: .cancel) {}
        }
    }
}

/// Everything the signed-in user has liked.
struct LikedPostsView: View {
    @Environment(SessionStore.self) private var session

    @Binding var path: NavigationPath

    @State private var posts: [Post] = []
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if posts.isEmpty {
                EmptyStateView(
                    symbol: "heart",
                    title: "No likes yet",
                    message: "Songs you like will show up here."
                )
            } else {
                List(posts) { post in
                    PostRow(
                        post: post,
                        onOpenPost: { path.append(post) },
                        onOpenAuthor: { path.append(post.author) },
                        onLike: { Task { await toggleLike(post) } }
                    )
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Liked")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        isLoading = posts.isEmpty
        posts = (try? await session.api.likedPosts(limit: 50))?.items ?? []
        isLoading = false
    }

    private func toggleLike(_ post: Post) async {
        guard let state = try? await session.api.unlike(postId: post.id) else { return }
        if state.isLiked == false {
            posts.removeAll { $0.id == post.id }
        }
    }
}

extension Bundle {
    var appVersion: String {
        let version = object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
        let build = object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"
        return "\(version) (\(build))"
    }
}
