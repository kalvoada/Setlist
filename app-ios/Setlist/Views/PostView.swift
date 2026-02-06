import SwiftUI

// TODO
// Design
// Comments
// Likes
// Share
// Content: Spotify/AppleMusic - Songs/Albums/Playlists

struct PostView: View {
    let post: Post
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("user: \(post.username)")
                .font(.headline)
                .foregroundColor(.blue)
            
            Text(post.content)
                .font(.body)
            
            HStack {
                Image(systemName: "heart")
                Text("\(post.likes)")
                Spacer()
            }
            .padding(.top, 4)
            .foregroundColor(.secondary)
        }
        .padding(.vertical, 8)
    }
}


