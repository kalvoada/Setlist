import SwiftUI

/// Settings › Edit profile: the things other people see.
struct EditProfileView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model = EditProfileViewModel()

    let onSaved: (User) -> Void

    init(onSaved: @escaping (User) -> Void) {
        self.onSaved = onSaved
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Spacer()
                        if let user = session.currentUser {
                            AvatarView(
                                user: previewUser(from: user),
                                size: 84
                            )
                        }
                        Spacer()
                    }
                    .listRowBackground(Color.clear)
                }

                Section("Display name") {
                    TextField("How your name appears", text: $model.displayName)
                        .textContentType(.name)
                }

                Section {
                    TextField("Tell people what you listen to", text: $model.bio, axis: .vertical)
                        .lineLimit(3...6)
                } header: {
                    Text("Bio")
                } footer: {
                    Text("\(max(0, model.bioRemaining)) characters left")
                        .foregroundStyle(model.bioRemaining < 0 ? .red : .secondary)
                }

                Section {
                    TextField("https://…", text: $model.avatarUrl)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                } header: {
                    Text("Avatar URL")
                } footer: {
                    Text("Paste a link to an image. Leave empty to use your initials.")
                }

                if let error = model.errorMessage {
                    Section {
                        Label(error, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Edit profile")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            if let updated = await model.save(using: session.api) {
                                onSaved(updated)
                                dismiss()
                            }
                        }
                    } label: {
                        if model.isSaving {
                            ProgressView().controlSize(.small)
                        } else {
                            Text("Save").fontWeight(.semibold)
                        }
                    }
                    .disabled(!model.hasChanges || model.isSaving || model.bioRemaining < 0)
                }
            }
            .task {
                if let user = session.currentUser {
                    model.start(from: user)
                }
            }
        }
    }

    /// Live preview of the avatar as the URL is typed.
    private func previewUser(from user: User) -> User {
        var copy = user
        copy.avatarUrl = model.avatarUrl
        copy.displayName = model.displayName
        return copy
    }
}
