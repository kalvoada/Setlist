import SwiftUI

// TODO:
// Add post
struct FeedView: View {
    @StateObject private var apiService = APIService()
    @State private var posts: [Post] = []
    
    var body: some View {
        NavigationStack {
            List(posts) { post in
                PostRow(post: post)
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            //.background(Color.athenaColorBlue)
            .refreshable {
                await loadPosts()
            }
            .task {
                await loadPosts()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                        Button {
                            // TODO: Action to add post
                        } label: {
                            Image(systemName: "plus")
                                .fontWeight(.bold)
                                .foregroundStyle(Color.athenaColorPink)
                        }
                    }
                
                ToolbarItem(placement: .principal) {
                        Text("SETLIST")
                            .font(.headline)
                            .fontWeight(.bold)
                            .tracking(5)
                            .foregroundStyle(Color.athenaColorPink)
                    }
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
