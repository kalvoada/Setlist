import SwiftUI
import SwiftData

// TODO:
// Options - edit profile/account
// Share profile
// Add post
// Bio
// Trackers - posts, friends, follows

private struct ProfileContentView: View {
    let user: User
    var isCurrentUser: Bool = false

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "person.crop.circle.fill")
                .resizable()
                .frame(width: 100, height: 100)
                .foregroundColor(.gray)

            Text(user.username)
                .font(.largeTitle)
                .bold()

            Text(user.bio ?? "No bio available")
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            // Action button differs between current user and others
            if isCurrentUser {
                Button("Edit Profile") {
                    // TODO: open edit profile sheet
                }
                .buttonStyle(.bordered)
            } else {
                Button("Follow") {
                    // TODO: follow/unfollow action
                }
                .buttonStyle(.borderedProminent)
                .tint(.athenaColorPink)
            }

            Divider()

            Text("Posts")
                .font(.headline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal)

            if let posts = user.posts {
                List(posts) { post in
                    PostRow(post: post, style: .profile)
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            } else {
                Text("No posts yet.")
                    .foregroundColor(.secondary)
                    .padding()
            }
        }
        .padding(.top)
    }
}

struct ProfileView: View {
    @State private var user: User?
    @StateObject private var apiService = APIService()

    // Hardcoding User ID 1 for now to simulate "Me"
    let currentUserId = 1

    var body: some View {
        NavigationStack {
            Group {
                if let user = user {
                    ProfileContentView(user: user, isCurrentUser: true)
                } else {
                    ProgressView("Loading Profile...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .navigationTitle("Profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        // TODO: settings / account options
                    } label: {
                        Image(systemName: "gearshape")
                            .foregroundStyle(Color.athenaColorPink)
                    }
                }
            }
            .task {
                await loadProfile()
            }
        }
    }

    func loadProfile() async {
        do {
            self.user = try await apiService.fetchUser(id: currentUserId)
        } catch {
            print("Error fetching profile: \(error)")
        }
    }
}

struct UserProfileView: View {
    let user: User

    var body: some View {
        ProfileContentView(user: user, isCurrentUser: false)
            .navigationTitle(user.username)
            .navigationBarTitleDisplayMode(.inline)
    }
}
