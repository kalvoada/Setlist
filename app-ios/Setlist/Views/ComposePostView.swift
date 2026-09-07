import SwiftUI

/// Share a song, album or playlist.
///
/// A post cannot exist without music, so the flow is built around the link:
/// paste it, the server resolves it, and only then does "Post" light up.
struct ComposePostView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss

    @State private var model = ComposePostViewModel()
    @FocusState private var linkFieldFocused: Bool

    /// Handed the created post so the caller can show it immediately.
    let onPosted: (Post) -> Void

    init(onPosted: @escaping (Post) -> Void) {
        self.onPosted = onPosted
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        TextField("Paste a Spotify or Apple Music link", text: $model.link)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)
                            .focused($linkFieldFocused)
                            .submitLabel(.done)
                            .onSubmit {
                                Task { await model.resolve(using: session.api) }
                            }

                        if model.isResolving {
                            ProgressView().controlSize(.small)
                        } else if !model.trimmedLink.isEmpty {
                            Button {
                                model.link = ""
                                model.clearPreview()
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.borderless)
                            .accessibilityLabel("Clear link")
                        }
                    }
                } header: {
                    Text("What are you listening to?")
                } footer: {
                    Text("Spotify, Apple Music, YouTube Music, SoundCloud, TIDAL, Deezer and Bandcamp links all work.")
                }

                if let preview = model.preview {
                    Section("Preview") {
                        MusicCardView(music: preview.asMusicItem, showsOpenButton: false)
                            .listRowInsets(EdgeInsets(top: 8, leading: 12, bottom: 8, trailing: 12))
                    }
                }

                Section("Say something (optional)") {
                    TextField("Why this one?", text: $model.caption, axis: .vertical)
                        .lineLimit(3...6)
                }

                if let error = model.errorMessage {
                    Section {
                        Label(error, systemImage: "exclamationmark.triangle")
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("New post")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            if let post = await model.submit(using: session.api) {
                                onPosted(post)
                                dismiss()
                            }
                        }
                    } label: {
                        if model.isPosting {
                            ProgressView().controlSize(.small)
                        } else {
                            Text("Post").fontWeight(.semibold)
                        }
                    }
                    .disabled(!model.canPost)
                }
            }
            .task {
                model.pasteFromClipboard()
                if !model.trimmedLink.isEmpty {
                    await model.resolve(using: session.api)
                } else {
                    linkFieldFocused = true
                }
            }
            .onChange(of: linkFieldFocused) { _, isFocused in
                if !isFocused {
                    Task { await model.resolve(using: session.api) }
                }
            }
        }
    }
}
