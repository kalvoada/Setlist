import SwiftUI

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

#Preview {
    ContentView()
        .modelContainer(SampleData.shared.modelContainer)
}
