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
            HStack {
                Image(systemName: "person.circle.fill")
                    .resizable()
                    .frame(width: 30, height: 30)
                    .foregroundColor(.blue)
                Text("User \(post.user_id)") // TODO get the user name
                    .font(.headline)
            }
            Text(post.content)
                .font(.body)
        }
        .padding(.vertical, 8)
    }
}


