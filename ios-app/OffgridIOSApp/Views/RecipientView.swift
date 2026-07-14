import SwiftUI

struct RecipientView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        OffgridPageContainer(contentTopPadding: 36) {
            OffgridSectionHeader(
                title: "Inbox",
                subtitle: "Messages relayed through a nearby phone arrive here, decrypted.",
                topPadding: 8
            )

            ConnectivityBadge()
                .frame(maxWidth: .infinity)

            Spacer(minLength: 12)

            if app.inbox.isEmpty {
                emptyState
            } else {
                VStack(spacing: 12) {
                    ForEach(app.inbox) { message in
                        messageCard(message)
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 14) {
            Image(systemName: "tray.fill")
                .font(.system(size: 36))
                .foregroundStyle(AppTheme.accent)
            Text("Waiting for messages")
                .font(.headline)
                .foregroundStyle(.white)
            Text("When a sender reaches a relay and the relay uploads to the cloud, new messages will show up here.")
                .font(.footnote)
                .foregroundStyle(AppTheme.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
        .offgridCard()
    }

    private func messageCard(_ message: InboxMessage) -> some View {
        VStack(spacing: 8) {
            Text(message.text)
                .font(.body)
                .foregroundStyle(.white)
                .multilineTextAlignment(.center)
            Text(message.at, style: .time)
                .font(.caption2)
                .foregroundStyle(AppTheme.muted)
        }
        .frame(maxWidth: .infinity)
        .offgridCard(padding: 14)
    }
}
