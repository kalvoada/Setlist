import Foundation

// A song, album or playlist shared from a streaming service.
struct MusicItem: Codable, Identifiable, Hashable {
    let id: Int
    let provider: String
    let providerName: String
    let itemType: String
    let url: String
    let title: String
    let artistName: String?
    let artworkUrl: String?
    let previewUrl: String?
    // The original service's own web player, when it has one.
    let embedUrl: String?
    // Where it opens for the signed-in user; nil until they pick a service.
    var native: NativeLink?

    var link: URL? { URL(string: url) }
    var artworkURL: URL? {
        guard let artworkUrl, !artworkUrl.isEmpty else { return nil }
        return URL(string: artworkUrl)
    }

    var kindName: String {
        switch itemType {
        case "track": return "Song"
        case "album": return "Album"
        case "playlist": return "Playlist"
        case "artist": return "Artist"
        default: return itemType.capitalized
        }
    }

    var subtitle: String { "\(kindName) · \(providerName)" }

    var symbolName: String {
        switch itemType {
        case "album": return "square.stack"
        case "playlist": return "music.note.list"
        case "artist": return "person.wave.2"
        default: return "music.note"
        }
    }

    init(
        id: Int,
        provider: String,
        providerName: String,
        itemType: String,
        url: String,
        title: String,
        artistName: String? = nil,
        artworkUrl: String? = nil,
        previewUrl: String? = nil,
        embedUrl: String? = nil,
        native: NativeLink? = nil
    ) {
        self.id = id
        self.provider = provider
        self.providerName = providerName
        self.itemType = itemType
        self.url = url
        self.title = title
        self.artistName = artistName
        self.artworkUrl = artworkUrl
        self.previewUrl = previewUrl
        self.embedUrl = embedUrl
        self.native = native
    }
}

// Where a music item opens for someone who picked a streaming service.
struct NativeLink: Codable, Hashable {
    enum Status: String, Codable {
        // `url` is the same item on the listener's service.
        case resolved
        // Can't be matched reliably (Bandcamp, SoundCloud, playlists): open the shared link.
        case original
        // Their service doesn't have it.
        case unavailable
        // Not looked up yet.
        case pending

        // A state this version doesn't know is treated as "ask the server".
        init(from decoder: Decoder) throws {
            let raw = try decoder.singleValueContainer().decode(String.self)
            self = Status(rawValue: raw) ?? .pending
        }
    }

    let status: Status
    let provider: String
    let providerName: String
    let url: String?
    // That service's own web player for `url`.
    var embedUrl: String?
}

extension MusicItem {
    // Where the music is played: which service, its link, and its web player.
    struct Destination: Equatable {
        let url: URL
        let service: String
        let provider: String
        let player: URL?

        enum Look: Equatable {
            // The service's own web player.
            case player(URL)
            // YouTube Music has no player to embed; the app draws its card.
            case youTubeMusic
            // The plain card: no player for it.
            case card
        }

        var look: Look {
            if let player { return .player(player) }
            return provider == "youtube_music" ? .youTubeMusic : .card
        }
    }

    // What the card shows for someone listening on `nativeProvider`.
    enum ListenAction: Equatable {
        case open(Destination)
        // Not on their service: say so and offer the shared link.
        case unavailable(service: String)
        // Not looked up yet, or looked up for a service they have since switched from.
        case lookUp
    }

    func listenAction(nativeProvider: String?) -> ListenAction? {
        guard let link else { return nil }
        let original = Destination(
            url: link, service: providerName, provider: provider, player: Self.player(embedUrl)
        )
        guard let nativeProvider else { return .open(original) }
        guard let native, native.provider == nativeProvider else { return .lookUp }

        switch native.status {
        case .resolved:
            guard let url = native.url.flatMap(URL.init(string:)) else {
                return .unavailable(service: native.providerName)
            }
            return .open(Destination(
                url: url,
                service: native.providerName,
                provider: native.provider,
                player: Self.player(native.embedUrl)
            ))
        case .original:
            return .open(original)
        case .unavailable:
            return .unavailable(service: native.providerName)
        case .pending:
            return .lookUp
        }
    }

    // Only the services' own players are ever loaded into a post.
    static let playerHosts: Set<String> = [
        "open.spotify.com", "embed.music.apple.com", "www.youtube.com",
        "w.soundcloud.com", "bandcamp.com"
    ]

    private static func player(_ string: String?) -> URL? {
        guard let url = string.flatMap(URL.init(string:)),
              url.scheme == "https",
              let host = url.host,
              playerHosts.contains(host)
        else { return nil }
        return url
    }
}

// Services a listener can pick: the ones the backend can match music into.
// Raw values are the API's provider ids.
enum MusicService: String, CaseIterable, Identifiable {
    case spotify
    case appleMusic = "apple_music"
    case youtubeMusic = "youtube_music"

    var id: String { rawValue }

    var name: String {
        switch self {
        case .spotify: return "Spotify"
        case .appleMusic: return "Apple Music"
        case .youtubeMusic: return "YouTube Music"
        }
    }
}

// A streaming link the backend resolved, shown while composing a post.
struct MusicLinkPreview: Codable, Hashable {
    let provider: String
    let providerName: String
    let itemType: String
    let url: String
    let title: String
    let artistName: String?
    let artworkUrl: String?
    let previewUrl: String?
    var embedUrl: String?

    var artworkURL: URL? {
        guard let artworkUrl, !artworkUrl.isEmpty else { return nil }
        return URL(string: artworkUrl)
    }

    var asMusicItem: MusicItem {
        MusicItem(
            id: 0,
            provider: provider,
            providerName: providerName,
            itemType: itemType,
            url: url,
            title: title,
            artistName: artistName,
            artworkUrl: artworkUrl,
            previewUrl: previewUrl,
            embedUrl: embedUrl
        )
    }
}

// A post: always a piece of music, optionally with something to say about it.
struct Post: Codable, Identifiable, Hashable {
    let id: Int
    var caption: String
    let createdAt: Date
    var author: User
    var music: MusicItem
    var likesCount: Int
    var commentsCount: Int
    var isLiked: Bool
    
    // Only returned by "GET /posts/{id}"
    var comments: [Comment]?

    var relativeDate: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: createdAt, relativeTo: .now)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        caption = try container.decodeIfPresent(String.self, forKey: .caption) ?? ""
        createdAt = try container.decode(Date.self, forKey: .createdAt)
        author = try container.decode(User.self, forKey: .author)
        music = try container.decode(MusicItem.self, forKey: .music)
        likesCount = try container.decodeIfPresent(Int.self, forKey: .likesCount) ?? 0
        commentsCount = try container.decodeIfPresent(Int.self, forKey: .commentsCount) ?? 0
        isLiked = try container.decodeIfPresent(Bool.self, forKey: .isLiked) ?? false
        comments = try container.decodeIfPresent([Comment].self, forKey: .comments)
    }

    init(
        id: Int,
        caption: String,
        createdAt: Date,
        author: User,
        music: MusicItem,
        likesCount: Int = 0,
        commentsCount: Int = 0,
        isLiked: Bool = false,
        comments: [Comment]? = nil
    ) {
        self.id = id
        self.caption = caption
        self.createdAt = createdAt
        self.author = author
        self.music = music
        self.likesCount = likesCount
        self.commentsCount = commentsCount
        self.isLiked = isLiked
        self.comments = comments
    }
}
