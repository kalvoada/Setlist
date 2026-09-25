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
}

extension MusicItem {
    // What the play button does for someone listening on `nativeProvider`.
    enum ListenAction: Equatable {
        case open(URL, service: String)
        // Not on their service: say so and offer the shared link.
        case unavailable(service: String)
        // Not looked up yet, or looked up for a service they have since switched from.
        case lookUp
    }

    func listenAction(nativeProvider: String?) -> ListenAction? {
        guard let link else { return nil }
        guard let nativeProvider else { return .open(link, service: providerName) }
        guard let native, native.provider == nativeProvider else { return .lookUp }

        switch native.status {
        case .resolved:
            guard let url = native.url.flatMap(URL.init(string:)) else {
                return .unavailable(service: native.providerName)
            }
            return .open(url, service: native.providerName)
        case .original:
            return .open(link, service: providerName)
        case .unavailable:
            return .unavailable(service: native.providerName)
        case .pending:
            return .lookUp
        }
    }
}

// Services a listener can pick: the ones the backend can match music into.
// Raw values are the API's provider ids.
enum MusicService: String, CaseIterable, Identifiable {
    case spotify
    case appleMusic = "apple_music"

    var id: String { rawValue }

    var name: String {
        switch self {
        case .spotify: return "Spotify"
        case .appleMusic: return "Apple Music"
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
            previewUrl: previewUrl
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
