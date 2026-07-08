import SwiftUI

struct RelayView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(app.peerCount > 0 ? "\(app.peerCount) device(s) connected" : "Waiting for nearby devices…",
                  systemImage: "point.3.connected.trianglepath.dotted")
                .font(.footnote)
                .foregroundStyle(app.peerCount > 0 ? .green : .secondary)

            Text("This phone carries other people's messages to the internet. It only ever sees ciphertext 🔒 — it can't read a single one.")
                .font(.footnote)
                .foregroundStyle(.secondary)

            if app.relayLog.isEmpty {
                Spacer()
                ContentUnavailableView("Nothing relayed yet",
                                       systemImage: "lock.shield",
                                       description: Text("Encrypted messages handed over by nearby phones will appear here."))
                Spacer()
            } else {
                List(app.relayLog) { entry in
                    VStack(alignment: .leading, spacing: 4) {
                        Text("→ recipient \(entry.recipient)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(entry.ciphertextPreview)
                            .font(.system(.callout, design: .monospaced))
                            .lineLimit(1)
                            .foregroundStyle(.orange)
                        Text(entry.status)
                            .font(.caption)
                            .foregroundStyle(entry.status.contains("✓") ? .green : .secondary)
                    }
                    .padding(.vertical, 2)
                }
                .listStyle(.plain)
            }
        }
        .padding()
        .navigationTitle("Relay")
        .navigationBarTitleDisplayMode(.inline)
    }
}
