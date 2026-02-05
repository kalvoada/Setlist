import SwiftUI
import SwiftData

struct FeedView: View {
    @Query(sort: \Post.username) private var posts: [Post]
        
    var body: some View {
        NavigationStack {
            List(posts) { post in
                PostView(post: post)
            }
            .navigationTitle("Setlist Feed")
            .listStyle(.plain)
        }
    }
}

#Preview {
    FeedView()
        .modelContainer(SampleData.shared.modelContainer)
}
