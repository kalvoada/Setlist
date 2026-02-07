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
            
            // FastAPI debug
            //DebugView().tabItem {
            //    Label("debug", systemImage: "plus")
            //}
        }
    }
}

#Preview {
    ContentView()
        .modelContainer(SampleData.shared.modelContainer)
}
