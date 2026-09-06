import SwiftUI

/// Sign in / sign up. The only screen a signed-out person can reach.
struct AuthView: View {
    private enum Mode: String, CaseIterable {
        case signIn = "Sign in"
        case signUp = "Create account"
    }

    @Environment(SessionStore.self) private var session

    @State private var mode: Mode = .signIn
    @State private var identifier = ""
    @State private var username = ""
    @State private var email = ""
    @State private var displayName = ""
    @State private var password = ""
    @State private var isWorking = false
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    header

                    Picker("Mode", selection: $mode) {
                        ForEach(Mode.allCases, id: \.self) { mode in
                            Text(mode.rawValue).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)

                    VStack(spacing: 12) {
                        if mode == .signIn {
                            field("Username or e-mail", text: $identifier, content: .username)
                        } else {
                            field("Username", text: $username, content: .username)
                            field("E-mail", text: $email, content: .emailAddress, keyboard: .emailAddress)
                            field("Display name (optional)", text: $displayName, content: .name, autocapitalize: .words)
                        }

                        SecureField("Password", text: $password)
                            .textContentType(mode == .signIn ? .password : .newPassword)
                            .textFieldStyle(.roundedBorder)
                            .submitLabel(.go)
                            .onSubmit { submit() }
                    }

                    if let errorMessage {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    Button(action: submit) {
                        HStack {
                            Spacer()
                            if isWorking {
                                ProgressView().tint(.white)
                            } else {
                                Text(mode.rawValue).fontWeight(.semibold)
                            }
                            Spacer()
                        }
                        .padding(.vertical, 6)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.setlistAccent)
                    .disabled(!canSubmit)

                    if mode == .signUp {
                        Text("Passwords need at least 8 characters. Usernames can use letters, numbers, dots and underscores.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .padding(24)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(Color.setlistBackground)
        }
    }

    private var header: some View {
        VStack(spacing: 8) {
            Image(systemName: "music.note.list")
                .font(.system(size: 48))
                .foregroundStyle(Color.setlistAccent)
            Text("SETLIST")
                .font(.largeTitle.bold())
                .tracking(6)
                .foregroundStyle(Color.setlistAccent)
            Text("Share what you're listening to.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(.top, 32)
    }

    private func field(
        _ title: String,
        text: Binding<String>,
        content: UITextContentType,
        keyboard: UIKeyboardType = .default,
        autocapitalize: TextInputAutocapitalization = .never
    ) -> some View {
        TextField(title, text: text)
            .textContentType(content)
            .keyboardType(keyboard)
            .textInputAutocapitalization(autocapitalize)
            .autocorrectionDisabled()
            .textFieldStyle(.roundedBorder)
    }

    private var canSubmit: Bool {
        guard !isWorking, password.count >= 8 else { return false }
        switch mode {
        case .signIn:
            return !identifier.trimmingCharacters(in: .whitespaces).isEmpty
        case .signUp:
            return username.trimmingCharacters(in: .whitespaces).count >= 3
                && email.contains("@")
        }
    }

    private func submit() {
        guard canSubmit else { return }
        isWorking = true
        errorMessage = nil

        Task {
            do {
                switch mode {
                case .signIn:
                    try await session.signIn(
                        identifier: identifier.trimmingCharacters(in: .whitespaces),
                        password: password
                    )
                case .signUp:
                    let name = displayName.trimmingCharacters(in: .whitespaces)
                    try await session.register(
                        username: username.trimmingCharacters(in: .whitespaces),
                        email: email.trimmingCharacters(in: .whitespaces),
                        password: password,
                        displayName: name.isEmpty ? nil : name
                    )
                }
            } catch {
                errorMessage = error.localizedDescription
            }
            isWorking = false
        }
    }
}
