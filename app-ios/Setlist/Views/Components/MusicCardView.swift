import SwiftUI
import WebKit

// A shared song or album. It plays in the listener's own service when the
// backend matched it there, and where it was shared for SoundCloud, Bandcamp or
// when no service is picked: in the service's web player, or YouTube Music's
// card. The plain card is the fallback: while looking it up, when the lookup
// failed, and when the listener's service doesn't have it ("Not available on
// Spotify").
struct MusicCardView: View {
    let music: MusicItem
    var artworkSize: CGFloat = 64
    // Off for a link that isn't posted yet: shows the original, looks nothing up.
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
        Group {
            switch look {
            case let .player(url):
                EmbeddedPlayer(url: url)
                    .frame(height: playerHeight(provider: destinationProvider,
                                                itemType: music.itemType))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            case .youTubeMusic:
                if case let .open(destination) = action {
                    YouTubeMusicCard(music: music, destination: destination)
                }
            case .card:
                card
            }
        }
        // Looked up as it scrolls into view, so it can show the right player.
        .task(id: nativeProvider) {
            if action == .lookUp { await lookUp(thenOpen: false) }
        }
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

    private var card: some View {
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
    }

    // MARK: - Where it plays

    private struct FallbackPrompt {
        let title: String
        var message: String?
    }

    private var nativeProvider: String? {
        showsOpenButton ? session.currentUser?.nativeProvider : nil
    }

    private var action: MusicItem.ListenAction? {
        var item = music
        if let lookedUp { item.native = lookedUp }
        return item.listenAction(nativeProvider: nativeProvider)
    }

    private var look: MusicItem.Destination.Look {
        guard case let .open(destination) = action else { return .card }
        return destination.look
    }

    private var destinationProvider: String {
        guard case let .open(destination) = action else { return music.provider }
        return destination.provider
    }

    // Names the service play will open, which is the listener's own once matched.
    private var subtitle: String {
        if case let .open(destination) = action { return "\(music.kindName) · \(destination.service)" }
        return music.subtitle
    }

    private var nativeServiceName: String {
        nativeProvider.flatMap(MusicService.init(rawValue:))?.name ?? "your music service"
    }

    private func accessibilityLabel(for action: MusicItem.ListenAction) -> String {
        switch action {
        case let .open(destination): return "Open in \(destination.service)"
        case let .unavailable(service): return "Not available on \(service)"
        case .lookUp: return "Open in \(nativeServiceName)"
        }
    }

    private func perform(_ action: MusicItem.ListenAction) async {
        switch action {
        case let .open(destination):
            openURL(destination.url) { accepted in
                if !accepted { fallback = FallbackPrompt(title: "Couldn't open \(destination.service)") }
            }
        case let .unavailable(service):
            fallback = FallbackPrompt(title: "Not available on \(service)")
        case .lookUp:
            await lookUp(thenOpen: true)
        }
    }

    // `thenOpen`: the listener tapped play, so failures are explained and a
    // match shown as the plain card is opened. A player or card just shows.
    private func lookUp(thenOpen: Bool) async {
        guard !isLookingUp else { return }
        isLookingUp = true
        defer { isLookingUp = false }

        do {
            lookedUp = try await session.api.nativeLink(musicId: music.id)
        } catch {
            if thenOpen, !error.isCancellation {
                fallback = FallbackPrompt(
                    title: "Couldn't check \(nativeServiceName)",
                    message: error.localizedDescription
                )
            }
            return
        }

        guard thenOpen else { return }
        // Still unknown (e.g. the service was changed meanwhile): don't loop.
        guard let next = action, next != .lookUp else {
            fallback = FallbackPrompt(title: "Couldn't check \(nativeServiceName)")
            return
        }
        if look == .card { await perform(next) }
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

// YouTube Music in its own colours. It has no player to embed, and YouTube's
// video player refuses many songs outside YouTube, so tapping it opens the app.
private struct YouTubeMusicCard: View {
    let music: MusicItem
    let destination: MusicItem.Destination

    @Environment(\.openURL) private var openURL

    private static let red = Color(red: 1, green: 0, blue: 0)
    private static let background = Color(red: 0.06, green: 0.06, blue: 0.06)

    var body: some View {
        Button {
            openURL(destination.url)
        } label: {
            HStack(spacing: 12) {
                AsyncImage(url: cover) { phase in
                    if case let .success(image) = phase {
                        image.resizable().scaledToFill()
                    } else {
                        Color.white.opacity(0.1)
                    }
                }
                .frame(width: 64, height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 6))

                VStack(alignment: .leading, spacing: 3) {
                    Text(music.title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                        .lineLimit(2)
                    if let artist = music.artistName, !artist.isEmpty {
                        Text(artist)
                            .font(.footnote)
                            .foregroundStyle(.white.opacity(0.7))
                            .lineLimit(1)
                    }
                    Label {
                        Text("YouTube Music")
                    } icon: {
                        Image(systemName: "play.circle.fill").foregroundStyle(Self.red)
                    }
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(.white.opacity(0.7))
                }

                Spacer(minLength: 4)

                Image(systemName: "play.fill")
                    .font(.body)
                    .foregroundStyle(.white)
                    .frame(width: 40, height: 40)
                    .background(Self.red, in: Circle())
            }
            .padding(Metrics.cardPadding)
            .background(Self.background, in: RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Play \(music.title) on YouTube Music")
    }

    // YouTube serves every video's cover at a fixed address; the 16:9 one,
    // cropped square, is the album art of a song.
    private var cover: URL? {
        let components = URLComponents(url: destination.url, resolvingAgainstBaseURL: false)
        guard let id = components?.queryItems?.first(where: { $0.name == "v" })?.value else {
            return music.artworkURL
        }
        return URL(string: "https://i.ytimg.com/vi/\(id)/mqdefault.jpg")
    }
}

// The height each service's player is designed for.
private func playerHeight(provider: String, itemType: String) -> CGFloat {
    let isTrack = itemType == "track"
    switch provider {
    case "spotify": return isTrack ? 152 : 352
    case "apple_music": return isTrack ? 175 : 450
    case "soundcloud": return isTrack ? 300 : 450
    default: return 120  // Bandcamp
    }
}

// A service's own web player, embedded the way a web page would (an iframe on
// an https page). Links out of it, like the title or
// "Open in Spotify", open the app or the browser instead of navigating the post.
struct EmbeddedPlayer: UIViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = .all

        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        guard context.coordinator.loadedURL != url else { return }
        context.coordinator.loadedURL = url
        webView.loadHTMLString(Self.page(embedding: url), baseURL: Self.pageOrigin)
    }

    // Any https origin will do; YouTube won't play in a page without one.
    private static let pageOrigin = URL(string: "https://setlist.app")!

    private static func page(embedding url: URL) -> String {
        let source = url.absoluteString
            .replacingOccurrences(of: "&", with: "&amp;")
            .replacingOccurrences(of: "\"", with: "&quot;")
        return """
        <!doctype html>
        <html><head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
        html, body { margin: 0; height: 100%; background: transparent; }
        iframe { border: 0; width: 100%; height: 100%; }
        </style>
        </head><body>
        <iframe src="\(source)" allowfullscreen
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          referrerpolicy="strict-origin-when-cross-origin"></iframe>
        </body></html>
        """
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        var loadedURL: URL?

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction
        ) async -> WKNavigationActionPolicy {
            guard navigationAction.navigationType == .linkActivated,
                  let url = navigationAction.request.url
            else { return .allow }
            _ = await UIApplication.shared.open(url)
            return .cancel
        }

        // Links that ask for a new window.
        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            if let url = navigationAction.request.url {
                UIApplication.shared.open(url)
            }
            return nil
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
            artistName: "Radiohead",
            embedUrl: "https://open.spotify.com/embed/track/1"
        )
    )
    .padding()
    .environment(SessionStore())
}
