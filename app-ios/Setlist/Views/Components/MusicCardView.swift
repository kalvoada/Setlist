import SwiftUI

// Album or playlist being shared. Play opens it on the listener's own service
// when it has been matched there, and says so when it hasn't.
struct MusicCardView: View {
    let music: MusicItem
    var artworkSize: CGFloat = 64
    var showsOpenButton: Bool = true

    @Environment(SessionStore.self) private var session
    @Environment(\.openURL) private var openURL

    // The server's answer when the card arrived before the lookup was done.
    @State private var lookedUp: NativeLink?
    @State private var isLookingUp = false
    @State private var fallback: FallbackPrompt?

    init(music: MusicItem, artworkSize: CGFloat = 64, showsOpenButton: Bool = true) {
        self.music = music
        self.artworkSize = artworkSize
        self.showsOpenButton = showsOpenButton
    }

    var body: some View {
        HStack(spacing: 12) {
            artwork

            VStack(alignment: .leading, spacing: 3) {
                Text(music.title)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(2)

                if let artist = music.artistName, !artist.isEmpty {
                    Text(artist)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Text(subtitle)
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(Color.setlistAccent)
                    .lineLimit(1)

                if case let .unavailable(service) = action {
                    Text("Not available on \(service)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer(minLength: 4)

            if showsOpenButton, let action {
                Button {
                    Task { await perform(action) }
                } label: {
                    if isLookingUp {
                        ProgressView().controlSize(.small)
                    } else {
                        Image(systemName: "play.circle.fill")
                            .font(.title2)
                            .foregroundStyle(Color.setlistAccent)
                    }
                }
                .buttonStyle(.borderless)
                .disabled(isLookingUp)
                .accessibilityLabel(accessibilityLabel(for: action))
            }
        }
        .padding(Metrics.cardPadding)
        .background(Color.setlistSurface, in: RoundedRectangle(cornerRadius: Metrics.cornerRadius))
        .accessibilityElement(children: .combine)
        .confirmationDialog(
            fallback?.title ?? "",
            isPresented: Binding(
                get: { fallback != nil },
                set: { if !$0 { fallback = nil } }
            ),
            titleVisibility: .visible,
            presenting: fallback
        ) { _ in
            if let link = music.link {
                Button("Open in \(music.providerName)") { openURL(link) }
            }
            Button("Cancel", role: .cancel) {}
        } message: { prompt in
            if let message = prompt.message { Text(message) }
        }
    }

    // MARK: - Opening

    private struct FallbackPrompt {
        let title: String
        var message: String?
    }

    private var nativeProvider: String? { session.currentUser?.nativeProvider }

    private var action: MusicItem.ListenAction? {
        var item = music
        if let lookedUp { item.native = lookedUp }
        return item.listenAction(nativeProvider: nativeProvider)
    }

    // Names the service play will open, which is the listener's own once matched.
    private var subtitle: String {
        if case let .open(_, service) = action { return "\(music.kindName) · \(service)" }
        return music.subtitle
    }

    private var nativeServiceName: String {
        nativeProvider.flatMap(MusicService.init(rawValue:))?.name ?? "your music service"
    }

    private func accessibilityLabel(for action: MusicItem.ListenAction) -> String {
        switch action {
        case let .open(_, service): return "Open in \(service)"
        case let .unavailable(service): return "Not available on \(service)"
        case .lookUp: return "Open in \(nativeServiceName)"
        }
    }

    private func perform(_ action: MusicItem.ListenAction) async {
        switch action {
        case let .open(url, service):
            openURL(url) { accepted in
                if !accepted { fallback = FallbackPrompt(title: "Couldn't open \(service)") }
            }
        case let .unavailable(service):
            fallback = FallbackPrompt(title: "Not available on \(service)")
        case .lookUp:
            await lookUp()
        }
    }

    private func lookUp() async {
        isLookingUp = true
        defer { isLookingUp = false }

        do {
            lookedUp = try await session.api.nativeLink(musicId: music.id)
        } catch {
            if !error.isCancellation {
                fallback = FallbackPrompt(
                    title: "Couldn't check \(nativeServiceName)",
                    message: error.localizedDescription
                )
            }
            return
        }

        // Still unknown (e.g. the service was changed meanwhile): don't loop.
        guard let next = action, next != .lookUp else {
            fallback = FallbackPrompt(title: "Couldn't check \(nativeServiceName)")
            return
        }
        await perform(next)
    }

    private var artwork: some View {
        Group {
            if let url = music.artworkURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case let .success(image):
                        image.resizable().scaledToFill()
                    case .failure:
                        artworkPlaceholder
                    default:
                        Color.setlistSurface
                    }
                }
            } else {
                artworkPlaceholder
            }
        }
        .frame(width: artworkSize, height: artworkSize)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var artworkPlaceholder: some View {
        ZStack {
            LinearGradient(
                colors: [Color.setlistAccent.opacity(0.8), Color.setlistMuted],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            Image(systemName: music.symbolName)
                .font(.system(size: artworkSize * 0.35))
                .foregroundStyle(.white)
        }
    }
}

// The same card for a link that has been resolved but not posted yet.
struct MusicPreviewCard: View {
    let preview: MusicLinkPreview
    var onRemove: (() -> Void)? = nil

    var body: some View {
        HStack(alignment: .top) {
            MusicCardView(music: preview.asMusicItem, showsOpenButton: false)

            if let onRemove {
                Button(action: onRemove) {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.borderless)
                .accessibilityLabel("Remove link")
            }
        }
    }
}

#Preview {
    MusicCardView(
        music: MusicItem(
            id: 1,
            provider: "spotify",
            providerName: "Spotify",
            itemType: "track",
            url: "https://open.spotify.com/track/1",
            title: "Weird Fishes / Arpeggi",
            artistName: "Radiohead"
        )
    )
    .padding()
    .environment(SessionStore())
}
