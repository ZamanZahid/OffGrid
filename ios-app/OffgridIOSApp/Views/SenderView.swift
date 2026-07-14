import SwiftUI

struct SenderView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        OffgridPageContainer(contentTopPadding: 20) {
            OffgridSectionHeader(
                title: "Sender",
                subtitle: "Write a message and hand it to a nearby relay over Bluetooth. (Like How Find-My Works.)",
                largeTitle: true,
                topPadding: 0
            )

            Spacer(minLength: 12)

            HStack {
                ConnectivityBadge()
                Spacer()
                peerBadge
            }

            StatusTimelineView(stage: app.sendStage)

            Spacer(minLength: 8)

            VStack(alignment: .leading, spacing: 10) {
                Text("Message")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(AppTheme.muted)
                    .textCase(.uppercase)
                    .frame(maxWidth: .infinity, alignment: .center)

                TextField("Type a message…", text: $app.draft, axis: .vertical)
                    .lineLimit(1...4)
                    .multilineTextAlignment(.center)
                    .padding(14)
                    .background(AppTheme.card)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .stroke(AppTheme.border, lineWidth: 1)
                    )
            }

            Button {
                app.sendDraft()
            } label: {
                Label("Send via nearby relay", systemImage: "paperplane.fill")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
            }
            .buttonStyle(.borderedProminent)
            .tint(AppTheme.accent)
            .disabled(app.draft.trimmingCharacters(in: .whitespaces).isEmpty || app.peerCount == 0)
        }
    }

    private var peerBadge: some View {
        HStack(spacing: 8) {
            Image(systemName: app.peerCount > 0 ? "dot.radiowaves.left.and.right" : "magnifyingglass")
            Text(app.peerCount > 0 ? "\(app.peerCount) relay nearby" : "No relay yet")
                .fontWeight(.medium)
        }
        .font(.caption)
        .foregroundStyle(app.peerCount > 0 ? AppTheme.success : AppTheme.muted)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background((app.peerCount > 0 ? AppTheme.success : Color.white).opacity(0.12))
        .clipShape(Capsule())
    }
}
