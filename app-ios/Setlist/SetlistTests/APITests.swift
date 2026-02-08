import XCTest
@testable import Setlist

// Mock Session
class MockURLSession: URLSessionProtocol {
    
    var result: Result<(Data, URLResponse), Error>?
    var requestHandler: ((URL) throws -> (Data, URLResponse))?
        
    func data(from url: URL) async throws -> (Data, URLResponse) {
    
        if let handler = requestHandler {
            return try handler(url)
        }
        
        if let result = result {
            switch result {
            case .success(let data):
                return data
            case .failure(let error):
                throw error
            }
        }
        
        fatalError("MockURLSession error: You must set 'result' or 'requestHandler' before running the test.")
    }
}

final class APIServiceTests: XCTestCase {
    
    var service: APIService!
    var mockSession: MockURLSession!
    
    override func setUp() {
        super.setUp()
        mockSession = MockURLSession()
        
        // Inject the mock session into the service
        service = APIService(session: mockSession)
    }
    
    override func tearDown() {
        service = nil
        mockSession = nil
        super.tearDown()
    }
    
    // MARK: - Tests
    
    func testFetchPosts_Success() async throws {
        
        let jsonString =
        """
        [
            { "content": "Hello", "user_id": 1, "id": 1 },
            { "content": "Swift", "user_id": 2, "id": 2 }
        ]
        """
        
        
        let data = jsonString.data(using: .utf8)!
        
        // Create a fake 200 OK response
        let response = HTTPURLResponse(url: URL(string: "http://test.com")!,
                                       statusCode: 200,
                                       httpVersion: nil,
                                       headerFields: nil)!
        
        // Tell the mock to return this data
        mockSession.result = .success((data, response))
        
        // Call the function
        let posts = try await service.fetchPosts()
        
        XCTAssertEqual(posts.count, 2)
    }
    
    func testFetchUser_Failure_404() async {
        // Create a 404 response
        let response = HTTPURLResponse(url: URL(string: "http://test.com")!,
                                       statusCode: 404,
                                       httpVersion: nil,
                                       headerFields: nil)!
        
        mockSession.result = .success((Data(), response))
        
        do {
            _ = try await service.fetchUser(id: 1)
            XCTFail("Should have thrown an error but didn't")
        } catch let error as APIError {
            XCTAssertEqual(error, APIError.invalidResponse)
        } catch {
            XCTFail("Threw the wrong type of error: \(error)")
        }
    }
    
    func testFetchUser_InvalidData() async {
        // Return garbage data
        let data = "Bad JSON Data".data(using: .utf8)!
        let response = HTTPURLResponse(url: URL(string: "http://test.com")!,
                                       statusCode: 200,
                                       httpVersion: nil,
                                       headerFields: nil)!
        
        mockSession.result = .success((data, response))
        
        do {
            _ = try await service.fetchUser(id: 99)
            XCTFail("Should have failed decoding")
        } catch let error as APIError {
            XCTAssertEqual(error, APIError.invalidData)
        } catch {
            XCTFail("Wrong error: \(error)")
        }
    }
    
    func testTwoUsers_Fetch() async throws {
 
        let user1Data = """
        { "id": 1, "username": "Alice", "bio": "I am User 1" }
        """.data(using: .utf8)!
        
        let user2Data = """
        { "id": 2, "username": "Bob", "bio": "I am User 2" }
        """.data(using: .utf8)!
        
        // Configure the Mock to check the URL and return the right person
        mockSession.requestHandler = { url in
            let response = HTTPURLResponse(url: url, statusCode: 200, httpVersion: nil, headerFields: nil)!
            
            if url.absoluteString.contains("/users/1") {
                return (user1Data, response)
            } else if url.absoluteString.contains("/users/2") {
                return (user2Data, response)
            } else {
                throw URLError(.fileDoesNotExist) // Fail if URL is weird
            }
        }
        

        async let fetchUser1 = service.fetchUser(id: 1)
        async let fetchUser2 = service.fetchUser(id: 2)
        
        // Wait for both to finish
        let (user1, user2) = try await (fetchUser1, fetchUser2)
        
        XCTAssertEqual(user1.username, "Alice")
        XCTAssertEqual(user1.id, 1)
        
        XCTAssertEqual(user2.username, "Bob")
        XCTAssertEqual(user2.id, 2)
    }
}
