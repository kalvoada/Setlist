import SwiftUI
import SwiftData

// TODO
// Design
// Options - edit profile/account
// Share profile
// Add post
// Bio
// Trackers - posts, friends, follows

struct ProfileView: View {
    @Query private var users: [User]
    @Query private var allPosts: [Post]
    
    var body: some View {
        if let user = users.first {
            
            VStack(spacing: 20) {
                Image(systemName: "person.circle.fill")
                    .resizable()
                    .frame(width: 100, height: 100)
                    .foregroundColor(.gray)
                
                Text((user.name))
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("bio?")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                Divider()
                
         
                
                List {
                    ForEach(postsFor(user: user)) { post in
                        PostView(post: post)
                    }
                }
                .listStyle(.plain)
                
                Spacer()
            }
            .padding()
        }
        else {
            Text("No users")
        }
    }
    
    
    private func postsFor(user: User) -> [Post] {
        return allPosts.filter { $0.username == user.name }
    }
}

#Preview {
    ProfileView()
        .modelContainer(SampleData.shared.modelContainer)
}
