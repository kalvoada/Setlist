import Foundation
import SwiftData


@Model
class Post {
    var username: String
    var content: String
    var likes: Int
    
    init(username: String, content: String, likes: Int) {
        self.username = username
        self.content = content
        self.likes = likes
    }
        
    static let sampleData = [
        Post(username: "Elena", content: "Just finished my first setlist!", likes: 15),
        Post(username: "Rody", content: "Anyone seen my guitar pick?", likes: 2)
    ]
}
