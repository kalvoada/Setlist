import SwiftUI

// TODO
// Design
// search (users) - later it will show recomended songs/albums
// separate tab for events

struct ContentView: View {
    var body: some View {
        TabView {
            FeedView().tabItem {
                Label("Feed", systemImage: "house")
            }
            
            ProfileView().tabItem {
                Label("Profile", systemImage: "person")
            }
        }
    }
}
