import Foundation

struct Post: Codable, Identifiable {
    let id: Int
    let content: String
    let user_id: Int
}
