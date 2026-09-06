import SwiftUI

// MARK: - SearchView
/// Find people to follow.
struct SearchView: View {
    @Environment(SessionStore.self) private var session

    @State private var model = SearchViewModel()
    @State private var searchText = ""

    var body: some View {
        NavigationStack {
            List {
                if searchText.isEmpty {
                    Section("Suggested for you") {
                        if model.suggestions.isEmpty {
                            Text("No suggestions right now.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(model.suggestions) { user in
                                UserRow(user: user, isMe: session.isCurrentUser(user)) {
                                    Task { await model.toggleFollow(user, using: session.api) }
                                }
                            }
                        }
                    }
                } else {
                    ForEach(model.results) { user in
                        UserRow(user: user, isMe: session.isCurrentUser(user)) {
                            Task { await model.toggleFollow(user, using: session.api) }
                        }
                    }
                }
            }
            .listStyle(.plain)
            .navigationTitle("Search")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: User.self) { user in
                UserProfileView(userId: user.id)
            }
            .searchable(
                text: $searchText,
                placement: .navigationBarDrawer(displayMode: .always),
                prompt: "Search people"
            )
            .textInputAutocapitalization(.never)
            .autocorrectionDisabled()
            .onChange(of: searchText) { _, newValue in
                model.search(query: newValue, using: session.api)
            }
            .overlay {
                if model.isSearching && model.results.isEmpty {
                    ProgressView()
                } else if !searchText.isEmpty, model.hasSearched, model.results.isEmpty {
                    ContentUnavailableView.search(text: searchText)
                }
            }
            .task { await model.loadSuggestions(using: session.api) }
            .refreshable { await model.loadSuggestions(using: session.api, force: true) }
        }
    }
}
