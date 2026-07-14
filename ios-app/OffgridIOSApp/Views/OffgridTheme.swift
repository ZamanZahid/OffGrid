import SwiftUI
import Network

enum AppTheme {
    static let backgroundTop = Color.black
    static let backgroundBottom = Color.black
    static let card = Color(red: 0.08, green: 0.08, blue: 0.10).opacity(0.94)
    static let cardElevated = Color(red: 0.10, green: 0.10, blue: 0.12).opacity(0.96)
    static let border = Color.white.opacity(0.14)
    static let accent = Color(red: 0.45, green: 0.62, blue: 1.0)
    static let accentSecondary = Color(red: 0.62, green: 0.48, blue: 0.98)
    static let success = Color(red: 0.35, green: 0.88, blue: 0.62)
    static let warning = Color(red: 1.0, green: 0.72, blue: 0.35)
    static let danger = Color(red: 1.0, green: 0.45, blue: 0.45)
    static let muted = Color.white.opacity(0.55)
}

enum AppTab: Int, CaseIterable, Hashable {
    case send, relay, inbox, skygaze

    var title: String {
        switch self {
        case .send: return "Send"
        case .relay: return "Relay"
        case .inbox: return "Inbox"
        case .skygaze: return "AeroGaze"
        }
    }

    var icon: String {
        switch self {
        case .send: return "paperplane"
        case .relay: return "antenna.radiowaves.left.and.right"
        case .inbox: return "tray"
        case .skygaze: return "star.fill"
        }
    }
}

final class ConnectivityMonitor: ObservableObject {
    @Published private(set) var isConnected = true
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "com.offgrid.connectivity")

    init() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                self?.isConnected = path.status == .satisfied
            }
        }
        monitor.start(queue: queue)
    }

    deinit {
        monitor.cancel()
    }
}

struct OffgridScreenBackground: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(Color.clear)
            .preferredColorScheme(.dark)
    }
}

extension View {
    func offgridScreenBackground() -> some View {
        modifier(OffgridScreenBackground())
    }

    func offgridCard(padding: CGFloat = 16) -> some View {
        self
            .padding(padding)
            .background(AppTheme.card)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(AppTheme.border, lineWidth: 1)
            )
    }
}

struct ConnectivityBadge: View {
    @EnvironmentObject private var connectivity: ConnectivityMonitor

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: connectivity.isConnected ? "wifi" : "wifi.slash")
            Text(connectivity.isConnected ? "Internet connected" : "No internet")
                .fontWeight(.medium)
        }
        .font(.caption)
        .foregroundStyle(connectivity.isConnected ? AppTheme.success : AppTheme.danger)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background((connectivity.isConnected ? AppTheme.success : AppTheme.danger).opacity(0.12))
        .clipShape(Capsule())
    }
}

struct OffgridPrimaryButton: View {
    let title: String
    let subtitle: String?
    let icon: String
    let tint: Color
    let iconOnTrailing: Bool
    let centerTitle: Bool
    let centerSubtitle: Bool
    let larger: Bool
    let action: () -> Void

    init(
        title: String,
        subtitle: String? = nil,
        icon: String,
        tint: Color = AppTheme.accent,
        iconOnTrailing: Bool = false,
        centerTitle: Bool = false,
        centerSubtitle: Bool = false,
        larger: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.subtitle = subtitle
        self.icon = icon
        self.tint = tint
        self.iconOnTrailing = iconOnTrailing
        self.centerTitle = centerTitle
        self.centerSubtitle = centerSubtitle
        self.larger = larger
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                if !iconOnTrailing {
                    iconView
                }

                VStack(alignment: centerSubtitle ? .center : .leading, spacing: 3) {
                    Text(title)
                        .font(larger ? .title3.weight(.semibold) : .headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity, alignment: centerTitle ? .center : .leading)
                    if let subtitle {
                        Text(subtitle)
                            .font(.caption)
                            .foregroundStyle(AppTheme.muted)
                            .multilineTextAlignment(centerSubtitle ? .center : .leading)
                            .frame(maxWidth: .infinity, alignment: centerSubtitle ? .center : .leading)
                    }
                }

                if iconOnTrailing {
                    iconView
                }

                Image(systemName: "chevron.right")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, larger ? 18 : 16)
            .background(AppTheme.cardElevated)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(larger ? tint.opacity(0.45) : AppTheme.border, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    private var iconView: some View {
        Image(systemName: icon)
            .font(larger ? .title2.weight(.semibold) : .title3.weight(.semibold))
            .foregroundStyle(tint)
            .frame(width: 34)
    }
}

struct OffgridSectionHeader: View {
    let title: String
    let subtitle: String
    var centered: Bool = true
    var largeTitle: Bool = false
    var topPadding: CGFloat = 0

    var body: some View {
        VStack(spacing: 8) {
            Text(title)
                .font(largeTitle ? .largeTitle.bold() : .title2.bold())
                .foregroundStyle(.white)
            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(AppTheme.muted)
                .multilineTextAlignment(centered ? .center : .leading)
        }
        .frame(maxWidth: .infinity, alignment: centered ? .center : .leading)
        .padding(.top, topPadding)
    }
}

struct OffgridBackButton: View {
    @EnvironmentObject private var app: AppModel

    var body: some View {
        Button {
            app.goHome()
        } label: {
            HStack(spacing: 6) {
                Image(systemName: "chevron.left")
                    .font(.subheadline.weight(.semibold))
                Text("Home")
                    .font(.subheadline.weight(.semibold))
            }
            .foregroundStyle(AppTheme.accent)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(AppTheme.card)
            .clipShape(Capsule())
            .overlay(Capsule().stroke(AppTheme.border, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

struct OffgridPageContainer<Content: View>: View {
    var contentTopPadding: CGFloat = 28
    @ViewBuilder let content: () -> Content

    var body: some View {
        ZStack {
            Color.clear

            VStack(spacing: 0) {
                HStack {
                    OffgridBackButton()
                    Spacer()
                }
                .padding(.horizontal, 20)
                .padding(.top, 12)
                .padding(.bottom, 4)

                ScrollView {
                    VStack(spacing: 20) {
                        content()
                    }
                    .frame(maxWidth: 480)
                    .frame(maxWidth: .infinity)
                    .padding(.horizontal, 20)
                    .padding(.top, contentTopPadding)
                    .padding(.bottom, 24)
                }
                .scrollContentBackground(.hidden)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.clear)
    }
}
