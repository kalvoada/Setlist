import SwiftUI

// TODO
// Design
// Add post - add song/playlist/album
struct FeedView: View {
    @StateObject private var apiService = APIService()
    @State private var posts: [Post] = []
    
    var body: some View {
        NavigationView {
            List(posts) { post in
                PostView(post: post)
            }
            .navigationTitle("Feed")
            .refreshable {
                await loadPosts()
            }
            .task {
                await loadPosts()
            }
        }
    }
    
    func loadPosts() async {
        do {
            self.posts = try await apiService.fetchPosts()
        } catch {
            print("Error fetching posts: \(error)")
        }
    }
}
