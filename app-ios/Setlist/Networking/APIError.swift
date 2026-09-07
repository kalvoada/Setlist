import Foundation

/// Everything the networking layer can fail with, in a form the UI can show.
enum APIError: Error, Equatable, LocalizedError {
    case invalidURL
    case invalidResponse
    case invalidData
    case unauthorized
    case notFound
    case conflict(String)
    case validation(String)
    case server(status: Int, message: String?)
    case offline
    case transport(String)
    /// The request was cancelled because the caller went away.
    case cancelled

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The app could not build a valid request."
        case .invalidResponse:
            return "The server sent an unexpected response."
        case .invalidData:
            return "The server sent data the app could not read."
        case .unauthorized:
            return "Your session has expired. Please sign in again."
        case .notFound:
            return "That content is no longer available."
        case let .conflict(message):
            return message
        case let .validation(message):
            return message
        case let .server(status, message):
            return message ?? "Something went wrong (error \(status))."
        case .offline:
            return "You appear to be offline. Check your connection and try again."
        case let .transport(message):
            return message
        case .cancelled:
            return "The request was cancelled."
        }
    }

    /// Maps an HTTP status onto the closest case, using the server's message.
    static func from(status: Int, message: String?) -> APIError {
        switch status {
        case 401:
            return .unauthorized
        case 403:
            return .validation(message ?? "You are not allowed to do that.")
        case 404:
            return .notFound
        case 409:
            return .conflict(message ?? "That is already taken.")
        case 400, 422:
            return .validation(message ?? "Please check what you entered.")
        default:
            return .server(status: status, message: message)
        }
    }
}

extension Error {
    /// True when the failure is just "you navigated away".
    ///
    /// Cancellation arrives as `CancellationError` from structured
    /// concurrency, as `URLError.cancelled` from URLSession, or as
    /// `APIError.cancelled` once it has been through `APIService`. Reporting
    /// any of them means an alert firing on a screen that is disappearing.
    var isCancellation: Bool {
        if self is CancellationError { return true }
        if let urlError = self as? URLError { return urlError.code == .cancelled }
        if let apiError = self as? APIError { return apiError == .cancelled }
        return false
    }
}
