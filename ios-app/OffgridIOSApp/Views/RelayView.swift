import SwiftUI

struct RelayView: View {
    @EnvironmentObject var app: AppModel
    @State private var serverHealthy: Bool? = nil

    var body: some View {
        OffgridPageContainer(contentTopPadding: 36) {
            OffgridSectionHeader(
                title: "Relay",
                subtitle: "This phone carries encrypted messages to the internet. It never sees plaintext.",
                topPadding: 8
            )

            HStack(spacing: 12) {
                ConnectivityBadge()
                Spacer()
                peerBadge
                serverBadge
            }
            .onAppear { checkServerHealth() }
            .onReceive(Timer.publish(every: 3.0, on: .main, in: .common).autoconnect()) { _ in
                checkServerHealth()
            }

            Text("Nearby senders hand off ciphertext here. Your phone uploads it when internet is available.")
                .font(.footnote)
                .foregroundStyle(AppTheme.muted)
                .multilineTextAlignment(.center)
                .offgridCard(padding: 14)

            Spacer(minLength: 16)

            if app.relayLog.isEmpty {
                emptyState
            } else {
                VStack(spacing: 12) {
                    ForEach(app.relayLog) { entry in
                        relayEntryCard(entry)
                    }
                }
            }
        }
    }

    private var peerBadge: some View {
        HStack(spacing: 8) {
            Image(systemName: "point.3.connected.trianglepath.dotted")
            Text(app.peerCount > 0 ? "\(app.peerCount) device(s)" : "No devices")
                .fontWeight(.medium)
        }
        .font(.caption)
        .foregroundStyle(app.peerCount > 0 ? AppTheme.success : AppTheme.muted)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background((app.peerCount > 0 ? AppTheme.success : Color.white).opacity(0.12))
        .clipShape(Capsule())
    }

    private var serverBadge: some View {
        HStack(spacing: 6) {
            Image(systemName: serverHealthy == true ? "checkmark.circle.fill" : serverHealthy == false ? "xmark.circle.fill" : "questionmark.circle.fill")
            Text(serverHealthy == true ? "Connected" : serverHealthy == false ? "Unreachable" : "Checking…")
                .fontWeight(.medium)
        }
        .font(.caption)
        .foregroundStyle(serverHealthy == true ? AppTheme.success : serverHealthy == false ? AppTheme.danger : AppTheme.muted)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background((
            serverHealthy == true ? AppTheme.success :
            serverHealthy == false ? AppTheme.danger :
            Color.white
        ).opacity(0.12))
        .clipShape(Capsule())
    }

    private func checkServerHealth() {
        Task {
            let url = ServerConfig.baseURL.appendingPathComponent("health")
            do {
                var req = URLRequest(url: url)
                req.timeoutInterval = 3
                let (_, response) = try await URLSession.shared.data(for: req)
                if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                    await MainActor.run { serverHealthy = true }
                } else {
                    await MainActor.run { serverHealthy = false }
                }
            } catch {
                await MainActor.run { serverHealthy = false }
                print("Server health check failed:", error)
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(AppTheme.accentSecondary.opacity(0.15))
                    .frame(width: 72, height: 72)
                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(AppTheme.accentSecondary)
            }
            Text("Nothing relayed yet")
                .font(.title3.weight(.semibold))
                .foregroundStyle(.white)
            Text("Encrypted messages handed over by nearby phones will appear here.")
                .font(.footnote)
                .foregroundStyle(AppTheme.muted)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 48)
        .padding(.horizontal, 8)
        .offgridCard()
    }

    private func relayEntryCard(_ entry: RelayLogEntry) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("→ recipient \(entry.recipient)")
                .font(.caption.weight(.semibold))
                .foregroundStyle(AppTheme.muted)

            Text(entry.ciphertextPreview)
                .font(.system(.callout, design: .monospaced))
                .lineLimit(1)
                .foregroundStyle(AppTheme.warning)

            Text(entry.status)
                .font(.caption)
                .foregroundStyle(entry.status.contains("✓") ? AppTheme.success : entry.status.contains("retrying") ? AppTheme.warning : AppTheme.danger)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .offgridCard(padding: 14)
    }
}
