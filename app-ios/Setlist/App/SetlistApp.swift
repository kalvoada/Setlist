import SwiftUI

@main
struct SetlistApp: App {
    @State private var session = SessionStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(session)
        }
    }
}
