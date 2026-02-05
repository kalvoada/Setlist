import Foundation
import SwiftData

@MainActor
class SampleData {
    static let shared = SampleData()
    let modelContainer: ModelContainer
    
    var context: ModelContext {
        modelContainer.mainContext
    }

    private init() {
        let schema = Schema([
            User.self,
            Post.self,
        ])
        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: true)

        do {
            modelContainer = try ModelContainer(for: schema, configurations: [modelConfiguration])
            insertSampleData()
            
            try context.save()
        } catch {
            fatalError("Could not create ModelContainer: \(error)")
        }
    }
    
    func insertSampleData() {
        for user in User.sampleData {
            modelContainer.mainContext.insert(user)
        }
        for post in Post.sampleData {
            modelContainer.mainContext.insert(post)
        }
    }
}
