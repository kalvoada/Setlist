import Foundation
import SwiftData


@Model
class User {
    var name: String
    
    init(name: String) {
        self.name = name
    }
    
    // Mock data
    static let sampleData = [
        User(name: "Elena"),
        User(name: "Graham"),
        User(name: "Mayuri"),
        User(name: "Rich"),
        User(name: "Rody"),
    ]
}
