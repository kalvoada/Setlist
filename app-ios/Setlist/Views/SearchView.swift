import SwiftUI

struct SearchView: View {
    @EnvironmentObject var apiService: APIService
    @State private var searchText = ""
    @State private var searchResults: [User] = []
    @State private var errorMessage: String?
    
    var body: some View {
        NavigationStack {
            List(searchResults) { user in
                NavigationLink(destination: UserProfileView(user: user)) {
                    HStack {
                        Image(systemName: "person.circle.fill")
                            .resizable()
                            .frame(width: 40, height: 40)
                            .foregroundColor(.gray)
                        
                        VStack(alignment: .leading) {
                            Text(user.username)
                                .font(.headline)
                            if let bio = user.bio, !bio.isEmpty {
                                Text(bio)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                            }
                        }
                    }
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $searchText, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search users...")
            .onChange(of: searchText) { oldValue, newValue in
                if newValue.isEmpty {
                    searchResults = []
                } else {
                    Task {
                        await performSearch(query: newValue)
                    }
                }
            }
            .overlay {
                if searchResults.isEmpty && !searchText.isEmpty {
                    ContentUnavailableView.search(text: searchText)
                }
            }
        }
    }
    
    func performSearch(query: String) async {
        // For now -> fetch directly (TODO)
        do {
            let users = try await apiService.searchUsers(query: query)
            await MainActor.run {
                self.searchResults = users
            }
        } catch {
            print("Search error: \(error)")
        }
    }
}
