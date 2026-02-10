import SwiftUI

// TODO
// Design
// create a view for other users profile
// search  -  recomended songs/albums
// separate tab for events

struct ContentView: View {
    var body: some View {
        TabView {
            FeedView().tabItem {
                Label("Feed", systemImage: "house")
            }
            
            SearchView().tabItem {
                Label("Search", systemImage: "magnifyingglass")
            }
            
            ProfileView().tabItem {
                Label("Profile", systemImage: "person")
            }
        }
    }
}
