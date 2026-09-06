import Foundation

/// A song, album or playlist shared from a streaming service.
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

    var link: URL? { URL(string: url) }
    var artworkURL: URL? {
        guard let artworkUrl, !artworkUrl.isEmpty else { return nil }
        return URL(string: artworkUrl)
    }

    /// "Album · Spotify", "Song · Apple Music", …
    var subtitle: String {
        let kind: String
        switch itemType {
        case "track": kind = "Song"
        case "album": kind = "Album"
        case "playlist": kind = "Playlist"
        case "artist": kind = "Artist"
        default: kind = itemType.capitalized
        }
        return "\(kind) · \(providerName)"
    }

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
        previewUrl: String? = nil
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
    }
}

/// A streaming link the backend resolved, shown while composing a post.
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

/// A post: always a piece of music, optionally with something to say about it.
struct Post: Codable, Identifiable, Hashable {
    let id: Int
    var caption: String
    let createdAt: Date
    var author: User
    var music: MusicItem
    var likesCount: Int
    var commentsCount: Int
    var isLiked: Bool
    /// Only returned by `GET /posts/{id}`.
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
