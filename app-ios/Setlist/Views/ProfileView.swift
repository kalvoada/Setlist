import SwiftUI
import SwiftData

// TODO:
// Design
// Options - edit profile/account
// Share profile
// Add post
// Bio
// Trackers - posts, friends, follows

struct ProfileView: View {
    @State private var user: User?
    @StateObject private var apiService = APIService()
    
    // Hardcoding User ID 1 for now to simulate "Me"
    let currentUserId = 1
    
    var body: some View {
        NavigationStack {
            VStack {
                if let user = user {
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
                        
                        Divider()
                        Text("Posts:")
                        
                        if let posts = user.posts {
                            List(posts) { post in
                                PostRow(post: post, style: .profile)
                            }
                            .listStyle(.plain)
                            .scrollContentBackground(.hidden)
                        }
                    }
                    .padding()
                } else {
                    ProgressView("Loading Profile...")
                }
            }
            .navigationTitle("Profile")
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
