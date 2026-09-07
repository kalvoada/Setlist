import SwiftUI

/// The heart on a post. Animates on tap and shows the running count.
struct LikeButton: View {
    let isLiked: Bool
    let count: Int
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Label {
                Text(count.formatted())
                    .font(.footnote.weight(.medium))
                    .monospacedDigit()
                    .contentTransition(.numericText())
            } icon: {
                Image(systemName: isLiked ? "heart.fill" : "heart")
                    .symbolEffect(.bounce, value: isLiked)
            }
            .foregroundStyle(isLiked ? Color.setlistAccent : Color.secondary)
        }
        .buttonStyle(.borderless)
        .accessibilityLabel(isLiked ? "Unlike" : "Like")
        .accessibilityValue("\(count) likes")
    }
}

/// Follow / Following, with a spinner while the request is in flight.
struct FollowButton: View {
    let isFollowing: Bool
    var isBusy: Bool = false
    var isCompact: Bool = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Group {
                if isBusy {
                    ProgressView().controlSize(.small)
                } else {
                    Text(isFollowing ? "Following" : "Follow")
                        .font(isCompact ? .footnote.weight(.semibold) : .body.weight(.semibold))
                }
            }
            .frame(minWidth: isCompact ? 80 : 120)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(isCompact ? .small : .regular)
        .tint(isFollowing ? Color.setlistMuted : Color.setlistAccent)
        .disabled(isBusy)
    }
}

/// One of the "12 Posts / 340 Followers / 89 Following" counters.
struct StatView: View {
    let value: Int
    let label: String

    var body: some View {
        VStack(spacing: 2) {
            Text(value.formatted())
                .font(.headline)
                .monospacedDigit()
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .combine)
    }
}
