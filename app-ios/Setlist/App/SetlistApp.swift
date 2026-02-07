import SwiftUI

@main
struct SetlistApp: App {
    @StateObject private var apiService = APIService()
    
    var body: some Scene {
        WindowGroup {
            ContentView().environmentObject(apiService)
        }
    }
}
