import Foundation

/// A Setlist account.
///
/// The API returns the same user object in three widths: a compact form
/// embedded in posts and comments, a summary with social counters, and the
/// signed-in user's own profile (which also carries `email`). Every field the
/// compact form omits decodes to a sensible default so one type covers all
/// three.
struct User: Codable, Identifiable, Hashable {
    let id: Int
    var username: String
    var displayName: String?
    var avatarUrl: String?
    var bio: String

    var followersCount: Int
    var followingCount: Int
    var postsCount: Int

    var isFollowing: Bool
    var isFollowedBy: Bool
    var isMe: Bool

    var createdAt: Date?
    /// Only present for the signed-in user.
    var email: String?

    /// What to show as the primary name in the UI.
    var name: String {
        let trimmed = displayName?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? username : trimmed
    }

    var handle: String { "@\(username)" }

    var initials: String {
        let source = name
        let letters = source.split(separator: " ").prefix(2).compactMap(\.first)
        return letters.isEmpty ? "?" : String(letters).uppercased()
    }

    var avatarURL: URL? {
        guard let avatarUrl, !avatarUrl.isEmpty else { return nil }
        return URL(string: avatarUrl)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        username = try container.decode(String.self, forKey: .username)
        displayName = try container.decodeIfPresent(String.self, forKey: .displayName)
        avatarUrl = try container.decodeIfPresent(String.self, forKey: .avatarUrl)
        bio = try container.decodeIfPresent(String.self, forKey: .bio) ?? ""
        followersCount = try container.decodeIfPresent(Int.self, forKey: .followersCount) ?? 0
        followingCount = try container.decodeIfPresent(Int.self, forKey: .followingCount) ?? 0
        postsCount = try container.decodeIfPresent(Int.self, forKey: .postsCount) ?? 0
        isFollowing = try container.decodeIfPresent(Bool.self, forKey: .isFollowing) ?? false
        isFollowedBy = try container.decodeIfPresent(Bool.self, forKey: .isFollowedBy) ?? false
        isMe = try container.decodeIfPresent(Bool.self, forKey: .isMe) ?? false
        createdAt = try container.decodeIfPresent(Date.self, forKey: .createdAt)
        email = try container.decodeIfPresent(String.self, forKey: .email)
    }

    init(
        id: Int,
        username: String,
        displayName: String? = nil,
        avatarUrl: String? = nil,
        bio: String = "",
        followersCount: Int = 0,
        followingCount: Int = 0,
        postsCount: Int = 0,
        isFollowing: Bool = false,
        isFollowedBy: Bool = false,
        isMe: Bool = false,
        createdAt: Date? = nil,
        email: String? = nil
    ) {
        self.id = id
        self.username = username
        self.displayName = displayName
        self.avatarUrl = avatarUrl
        self.bio = bio
        self.followersCount = followersCount
        self.followingCount = followingCount
        self.postsCount = postsCount
        self.isFollowing = isFollowing
        self.isFollowedBy = isFollowedBy
        self.isMe = isMe
        self.createdAt = createdAt
        self.email = email
    }
}
