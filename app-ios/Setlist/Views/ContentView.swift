import SwiftUI

// MARK: - ContentView
/// Root of the app: shows the welcome screen or the tabs, depending on whether
/// there is a signed-in user.
struct ContentView: View {
    @Environment(SessionStore.self) private var session

    init() {
        ContentView.configureAppearance()
    }

    var body: some View {
        Group {
            switch session.phase {
            case .restoring:
                LaunchView()
            case .signedOut:
                AuthView()
            case .signedIn:
                MainTabView()
            }
        }
        .animation(.easeInOut(duration: 0.25), value: session.phase)
        .task { await session.restore() }
    }

    // MARK: - Bars
    private static func configureAppearance() {
        let tabAppearance = UITabBarAppearance()
        tabAppearance.configureWithOpaqueBackground()
        tabAppearance.backgroundColor = UIColor.athenaColorBlue

        let unselectedColor = UIColor.athenaColorLightPink
        tabAppearance.stackedLayoutAppearance.normal.iconColor = unselectedColor
        tabAppearance.stackedLayoutAppearance.normal.titleTextAttributes = [
            .foregroundColor: unselectedColor
        ]

        UITabBar.appearance().standardAppearance = tabAppearance
        UITabBar.appearance().scrollEdgeAppearance = tabAppearance

        let navAppearance = UINavigationBarAppearance()
        navAppearance.configureWithOpaqueBackground()
        navAppearance.backgroundColor = UIColor.athenaColorBlue
        navAppearance.titleTextAttributes = [.foregroundColor: UIColor.athenaColorPink]
        navAppearance.largeTitleTextAttributes = [.foregroundColor: UIColor.athenaColorPink]

        UINavigationBar.appearance().standardAppearance = navAppearance
        UINavigationBar.appearance().compactAppearance = navAppearance
        UINavigationBar.appearance().scrollEdgeAppearance = navAppearance
    }
}

// MARK: - MainTabView
struct MainTabView: View {
    var body: some View {
        TabView {
            FeedView()
                .tabItem { Label("Feed", systemImage: "house") }

            SearchView()
                .tabItem { Label("Search", systemImage: "magnifyingglass") }

            ProfileView()
                .tabItem { Label("Profile", systemImage: "person") }
        }
        .tint(.setlistAccent)
    }
}

// MARK: - LaunchView
/// Shown for the moment it takes to restore a stored session.
struct LaunchView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "music.note.list")
                .font(.system(size: 44))
                .foregroundStyle(Color.setlistAccent)
            ProgressView()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.setlistBackground)
    }
}
