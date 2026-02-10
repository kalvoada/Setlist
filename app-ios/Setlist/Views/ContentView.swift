import SwiftUI

// TODO:
// Design - search and profile
// Feed - plus adds a post
// Profile - options, edit bio, trackers (followers...)
//      create separate a view for other users profile
// Post - like, comment, content (songs...)
// search  -  recomended songs/albums
// separate tab for events

struct ContentView: View {
    init() {
        
        // MARK: - Bottom bar
        let tabAppearance = UITabBarAppearance()
        tabAppearance.configureWithOpaqueBackground()
        tabAppearance.backgroundColor = UIColor.athenaColorBlue
        
        let unselectedColor = UIColor.athenaColorLightPink
        tabAppearance.stackedLayoutAppearance.normal.iconColor = unselectedColor
        
        UITabBar.appearance().standardAppearance = tabAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabAppearance
        
        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        
        // MARK: - Top bar
        navAppearance.backgroundColor = UIColor.athenaColorBlue
        
        navAppearance.titleTextAttributes = [.foregroundColor: UIColor.athenaColorPink]
        navAppearance.largeTitleTextAttributes = [.foregroundColor: UIColor.athenaColorPink]
        
        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
    }

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
        .tint(.athenaColorPink)
    }
}
