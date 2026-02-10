import Foundation
import SwiftUI


protocol URLSessionProtocol {
    func data(from url: URL) async throws -> (Data, URLResponse)
}

extension URLSession: URLSessionProtocol {}

class APIService: ObservableObject {
    let baseURL = "http://127.0.0.1:8000"
    let session: URLSessionProtocol
    
    init(session: URLSessionProtocol = URLSession.shared) {
        self.session = session
    }
    
    func fetchPosts() async throws -> [Post] {
        let endpoint = "\(baseURL)/posts/"
        
        guard let url = URL(string: endpoint) else {
            return []
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let response = response as? HTTPURLResponse, response.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        do {
            let decoder = JSONDecoder()

            return try decoder.decode([Post].self, from: data)
        } catch {
            throw APIError.invalidData
        }
    }
    
    
    
    func fetchUser(id: Int) async throws -> User {
        let endpoint = "\(baseURL)/users/\(id)"
        
        guard let url = URL(string: endpoint) else {
            throw APIError.invalidURL
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let response = response as? HTTPURLResponse, response.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(User.self, from: data)
        } catch {
            throw APIError.invalidData
        }
    }
    
    func searchUsers(query: String) async throws -> [User] {
        var urlComponents = URLComponents(string: "\(baseURL)/users/search")
        
        urlComponents?.queryItems = [
            URLQueryItem(name: "q", value: query)
        ]
        
        guard let url = urlComponents?.url else {
            throw APIError.invalidURL
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let response = response as? HTTPURLResponse, response.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        do {
            let decoder = JSONDecoder()
            return try decoder.decode([User].self, from: data)
        } catch {
            throw APIError.invalidData
        }
    }
}

enum APIError: Error {
    case invalidURL
    case invalidResponse
    case invalidData
}
