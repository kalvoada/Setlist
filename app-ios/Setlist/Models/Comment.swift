import Foundation

struct Comment: Codable, Identifiable {
    let id: Int
    let content: String
    let user_id: Int
    let post_id: Int
}
