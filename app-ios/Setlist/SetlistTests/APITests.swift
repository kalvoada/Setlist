import XCTest
@testable import Setlist

// Mock Session
class MockURLSession: URLSessionProtocol {
    var result: Result<(Data, URLResponse), Error>?
    
    func data(from url: URL) async throws -> (Data, URLResponse) {
        guard let result = result else {
            fatalError("Result not set in MockURLSession")
        }
        
        switch result {
        case .success(let data):
            return data
        case .failure(let error):
            throw error
        }
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
}
