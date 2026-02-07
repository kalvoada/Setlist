import Foundation

struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let bio: String?
    let posts: [Post]?
}
