import SwiftUI

/// A user's avatar, falling back to their initials on the brand colour.
struct AvatarView: View {
    let user: User
    var size: CGFloat = 44

    var body: some View {
        Group {
            if let url = user.avatarURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case let .success(image):
                        image.resizable().scaledToFill()
                    case .failure:
                        placeholder
                    default:
                        Color.setlistSurface
                    }
                }
            } else {
                placeholder
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .overlay(Circle().stroke(Color.setlistSeparator.opacity(0.4), lineWidth: 0.5))
        .accessibilityHidden(true)
    }

    private var placeholder: some View {
        ZStack {
            Color.setlistMuted
            Text(user.initials)
                .font(.system(size: size * 0.4, weight: .semibold, design: .rounded))
                .foregroundStyle(.white)
        }
    }
}

#Preview {
    HStack {
        AvatarView(user: User(id: 1, username: "mia", displayName: "Mia Novak"), size: 64)
        AvatarView(user: User(id: 2, username: "adam"), size: 44)
    }
}
