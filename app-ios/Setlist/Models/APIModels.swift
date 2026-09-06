import Foundation

// MARK: - Envelopes

/// Every list endpoint returns this envelope.
struct Page<Item: Decodable>: Decodable {
    let items: [Item]
    let limit: Int
    let offset: Int
    let total: Int
    let hasMore: Bool

    static var empty: Page<Item> {
        Page(items: [], limit: 0, offset: 0, total: 0, hasMore: false)
    }

    init(items: [Item], limit: Int, offset: Int, total: Int, hasMore: Bool) {
        self.items = items
        self.limit = limit
        self.offset = offset
        self.total = total
        self.hasMore = hasMore
    }
}

struct AuthResponse: Decodable {
    let accessToken: String
    let tokenType: String
    let expiresIn: Int
    let user: User
}

struct LikeState: Decodable {
    let postId: Int
    let isLiked: Bool
    let likesCount: Int
}

struct FollowState: Decodable {
    let userId: Int
    let isFollowing: Bool
    let followersCount: Int
}

/// FastAPI error bodies: `{"detail": "…"}` or `{"detail": [{"msg": "…"}]}`.
struct APIErrorBody: Decodable {
    let detail: String?

    private struct ValidationError: Decodable {
        let msg: String
        let loc: [LocationComponent]?

        enum LocationComponent: Decodable {
            case string(String)
            case int(Int)

            init(from decoder: Decoder) throws {
                let container = try decoder.singleValueContainer()
                if let value = try? container.decode(String.self) {
                    self = .string(value)
                } else {
                    self = .int(try container.decode(Int.self))
                }
            }

            var text: String? {
                if case let .string(value) = self { return value }
                return nil
            }
        }

        /// "Music url: Field required" reads better than "Field required".
        var message: String {
            guard let field = loc?.compactMap(\.text).last(where: { $0 != "body" }) else {
                return msg
            }
            let label = field.replacingOccurrences(of: "_", with: " ")
            return "\(label.prefix(1).uppercased())\(label.dropFirst()): \(msg)"
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let text = try? container.decode(String.self, forKey: .detail) {
            detail = text
        } else if let errors = try? container.decode([ValidationError].self, forKey: .detail) {
            detail = errors.map(\.message).joined(separator: "\n")
        } else {
            detail = nil
        }
    }

    private enum CodingKeys: String, CodingKey { case detail }
}

// MARK: - Request bodies

struct RegisterRequest: Encodable {
    let username: String
    let email: String
    let password: String
    let displayName: String?
}

struct LoginRequest: Encodable {
    let identifier: String
    let password: String
}

struct ProfileUpdateRequest: Encodable {
    var displayName: String?
    var bio: String?
    var avatarUrl: String?
}

struct AccountUpdateRequest: Encodable {
    let currentPassword: String
    var username: String?
    var email: String?
    var newPassword: String?
}

struct AccountDeleteRequest: Encodable {
    let currentPassword: String
}

struct CreatePostRequest: Encodable {
    let musicUrl: String
    let caption: String
    var title: String?
    var artistName: String?
    var artworkUrl: String?
    var previewUrl: String?
}

struct UpdatePostRequest: Encodable {
    let caption: String
}

struct CreateCommentRequest: Encodable {
    let content: String
}

struct ResolveLinkRequest: Encodable {
    let url: String
}
