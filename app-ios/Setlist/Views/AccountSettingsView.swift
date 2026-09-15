import SwiftUI

/// Settings › Account: the credentials behind the profile.
///
/// Username, e-mail and password changes all require the current password, and
/// deleting the account asks for it again — both enforced by the server too.
struct AccountSettingsView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model = AccountSettingsViewModel()
    @State private var showingDeleteSheet = false

    var body: some View {
        Form {
            Section {
                TextField("Username", text: $model.username)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textContentType(.username)
            } header: {
                Text("Username")
            } footer: {
                Text("Letters, numbers, dots and underscores. This is how people find you.")
            }

            Section("E-mail") {
                TextField("you@example.com", text: $model.email)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
            }

            Section {
                SecureField("New password", text: $model.newPassword)
                    .textContentType(.newPassword)
                SecureField("Confirm new password", text: $model.confirmPassword)
                    .textContentType(.newPassword)
            } header: {
                Text("Change password")
            } footer: {
                Text("At least 8 characters. Leave empty to keep your current password.")
            }

            Section {
                SecureField("Current password", text: $model.currentPassword)
                    .textContentType(.password)
            } header: {
                Text("Confirm it's you")
            } footer: {
                if let message = model.validationMessage {
                    Text(message).foregroundStyle(.red)
                } else if let error = model.errorMessage {
                    Text(error).foregroundStyle(.red)
                } else if let success = model.successMessage {
                    Text(success).foregroundStyle(.green)
                }
            }

            Section {
                Button(role: .destructive) {
                    showingDeleteSheet = true
                } label: {
                    Label("Delete account", systemImage: "trash")
                }
            } footer: {
                Text("Deleting removes your profile, posts, comments and likes for good.")
            }
        }
        .navigationTitle("Account")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button {
                    Task {
                        if let updated = await model.save(using: session.api) {
                            session.apply(updated)
                        }
                    }
                } label: {
                    if model.isSaving {
                        ProgressView().controlSize(.small)
                    } else {
                        Text("Save").fontWeight(.semibold)
                    }
                }
                .disabled(!model.canSave)
            }
        }
        .sheet(isPresented: $showingDeleteSheet) {
            DeleteAccountSheet(model: model)
                .presentationDetents([.medium])
        }
        .task {
            if let user = session.currentUser {
                model.start(from: user)
            }
        }
    }
}

/// Last chance before the account goes away.
private struct DeleteAccountSheet: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    let model: AccountSettingsViewModel

    @State private var password = ""
    @State private var confirmed = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("This deletes your profile, every post you shared, your comments and your likes. It cannot be undone.")
                        .font(.subheadline)
                }

                Section("Password") {
                    SecureField("Current password", text: $password)
                        .textContentType(.password)
                }

                Section {
                    Toggle("I understand this is permanent", isOn: $confirmed)
                }

                if let error = model.errorMessage {
                    Section {
                        Text(error).foregroundStyle(.red).font(.footnote)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        Task {
                            if await model.deleteAccount(password: password, using: session.api) {
                                dismiss()
                                session.signOut()
                            }
                        }
                    } label: {
                        HStack {
                            Spacer()
                            if model.isDeleting {
                                ProgressView()
                            } else {
                                Text("Delete my account").fontWeight(.semibold)
                            }
                            Spacer()
                        }
                    }
                    .disabled(password.isEmpty || !confirmed || model.isDeleting)
                }
            }
            .navigationTitle("Delete account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
