import Foundation

struct Comment: Codable, Identifiable, Hashable {
    let id: Int
    let content: String
    let postId: Int
    let createdAt: Date
    let author: User

    var relativeDate: String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: createdAt, relativeTo: .now)
    }
}
