import SwiftUI

/// The heart of a Setlist post: the song, album or playlist being shared.
struct MusicCardView: View {
    let music: MusicItem
    var artworkSize: CGFloat = 64
    var showsOpenButton: Bool = true

    @Environment(\.openURL) private var openURL

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

                Text(music.subtitle)
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(Color.setlistAccent)
                    .lineLimit(1)
            }

            Spacer(minLength: 4)

            if showsOpenButton, let link = music.link {
                Button {
                    openURL(link)
                } label: {
                    Image(systemName: "play.circle.fill")
                        .font(.title2)
                        .foregroundStyle(Color.setlistAccent)
                }
                .buttonStyle(.borderless)
                .accessibilityLabel("Open in \(music.providerName)")
            }
        }
        .padding(Metrics.cardPadding)
        .background(Color.setlistSurface, in: RoundedRectangle(cornerRadius: Metrics.cornerRadius))
        .accessibilityElement(children: .combine)
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

/// The same card for a link that has been resolved but not posted yet.
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
}
