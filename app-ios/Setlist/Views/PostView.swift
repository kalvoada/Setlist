import SwiftUI

// TODO
// username
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
                    .foregroundColor(.athenaColorDarkBlue)
                    .clipShape(Circle())
                Text("User \(post.user_id)") // TODO get the user name
                    .font(.headline)
                    .foregroundColor(Color.athenaColorPink)
            }
            Text(post.content)
                .font(.body)
        }
        
        .padding(.vertical, 8)
    }
}


