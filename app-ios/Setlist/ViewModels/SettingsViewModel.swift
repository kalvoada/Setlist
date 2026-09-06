import Foundation
import Observation

/// Settings › Edit profile.
@MainActor
@Observable
final class EditProfileViewModel {
    var displayName: String = ""
    var bio: String = ""
    var avatarUrl: String = ""
    private(set) var isSaving = false
    var errorMessage: String?

    private var original: User?

    func start(from user: User) {
        guard original == nil else { return }
        original = user
        displayName = user.displayName ?? ""
        bio = user.bio
        avatarUrl = user.avatarUrl ?? ""
    }

    var hasChanges: Bool {
        guard let original else { return false }
        return displayName != (original.displayName ?? "")
            || bio != original.bio
            || avatarUrl != (original.avatarUrl ?? "")
    }

    var bioRemaining: Int { 300 - bio.count }

    func save(using api: APIService) async -> User? {
        isSaving = true
        errorMessage = nil
        defer { isSaving = false }

        do {
            return try await api.updateProfile(
                displayName: displayName.trimmingCharacters(in: .whitespacesAndNewlines),
                bio: bio.trimmingCharacters(in: .whitespacesAndNewlines),
                avatarUrl: avatarUrl.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }
}

/// Settings › Account. Every change is confirmed with the current password.
@MainActor
@Observable
final class AccountSettingsViewModel {
    var username: String = ""
    var email: String = ""
    var newPassword: String = ""
    var confirmPassword: String = ""
    var currentPassword: String = ""

    private(set) var isSaving = false
    private(set) var isDeleting = false
    var errorMessage: String?
    var successMessage: String?

    private var original: User?

    func start(from user: User) {
        guard original == nil else { return }
        original = user
        username = user.username
        email = user.email ?? ""
    }

    var changedUsername: String? {
        let trimmed = username.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed == original?.username ? nil : trimmed
    }

    var changedEmail: String? {
        let trimmed = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return trimmed == (original?.email ?? "") ? nil : trimmed
    }

    var hasChanges: Bool {
        changedUsername != nil || changedEmail != nil || !newPassword.isEmpty
    }

    var canSave: Bool {
        hasChanges && !currentPassword.isEmpty && !isSaving && validationMessage == nil
    }

    /// Client-side checks that mirror the server's rules, so the user finds
    /// out before a round trip.
    var validationMessage: String? {
        if let username = changedUsername {
            if username.count < 3 || username.count > 30 {
                return "Username must be between 3 and 30 characters."
            }
            let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._"))
            if username.unicodeScalars.contains(where: { !allowed.contains($0) }) {
                return "Usernames can only contain letters, numbers, dots and underscores."
            }
        }
        if let email = changedEmail, !email.contains("@") || !email.contains(".") {
            return "Enter a valid e-mail address."
        }
        if !newPassword.isEmpty {
            if newPassword.count < 8 {
                return "New password must be at least 8 characters."
            }
            if newPassword != confirmPassword {
                return "The new passwords do not match."
            }
        }
        return nil
    }

    func save(using api: APIService) async -> User? {
        guard canSave else { return nil }

        isSaving = true
        errorMessage = nil
        successMessage = nil
        defer { isSaving = false }

        do {
            let user = try await api.updateAccount(
                currentPassword: currentPassword,
                username: changedUsername,
                email: changedEmail,
                newPassword: newPassword.isEmpty ? nil : newPassword
            )
            original = user
            currentPassword = ""
            newPassword = ""
            confirmPassword = ""
            successMessage = "Account updated."
            return user
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    func deleteAccount(password: String, using api: APIService) async -> Bool {
        isDeleting = true
        errorMessage = nil
        defer { isDeleting = false }

        do {
            try await api.deleteAccount(currentPassword: password)
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}
