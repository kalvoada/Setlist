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
            Post(username: "Rody", content: "Anyone seen my guitar pick?", likes: 2),
            
            Post(username: "Graham", content: "Late-night jam sessions hit different.", likes: 23),
            Post(username: "Mayuri", content: "Experimenting with a new synth patch 🎛️", likes: 18),
            Post(username: "Rich", content: "Soundcheck went smoother than expected.", likes: 9),
            
            Post(username: "Elena", content: "Coffee + lyrics = progress ☕️", likes: 31),
            Post(username: "Rody", content: "Broke a string mid-practice. Classic.", likes: 7),
            Post(username: "Graham", content: "Tempo debates are getting intense.", likes: 12),
            
            Post(username: "Mayuri", content: "Does anyone else label their cables or is it just me?", likes: 27),
            Post(username: "Rich", content: "Found an old demo from 2016. Yikes.", likes: 19),
            
            Post(username: "Elena", content: "Thinking of changing the chorus — thoughts?", likes: 22),
            Post(username: "Rody", content: "Pedalboard finally feels complete. For now.", likes: 34),
            Post(username: "Graham", content: "Metronomes are both a blessing and a curse.", likes: 16)
    ]
}
