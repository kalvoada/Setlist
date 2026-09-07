import SwiftUI

// MARK: - Theme
/// Semantic names for the brand palette in `Assets.xcassets`, so screens read
/// as intent ("accent", "surface") rather than as raw colour names.
extension Color {
    /// Primary brand colour: buttons, likes, active tabs.
    static let setlistAccent = Color.athenaColorPink
    /// Secondary brand colour, used on top of the accent.
    static let setlistAccentSoft = Color.athenaColorLightPink
    /// Navigation and tab bar fill.
    static let setlistBar = Color.athenaColorBlue
    /// Avatar placeholders and quiet iconography.
    static let setlistMuted = Color.athenaColorDarkBlue

    static let setlistBackground = Color(uiColor: .systemBackground)
    static let setlistSurface = Color(uiColor: .secondarySystemBackground)
    static let setlistSeparator = Color(uiColor: .separator)
}

enum Metrics {
    static let cornerRadius: CGFloat = 14
    static let cardPadding: CGFloat = 12
    static let rowSpacing: CGFloat = 10
}
