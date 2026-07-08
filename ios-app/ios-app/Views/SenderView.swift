import SwiftUI

struct SenderView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        VStack(spacing: 20) {
            // Proof this phone is offline + whether a relay is in range.
            HStack {
                Label("No internet", systemImage: "wifi.slash")
                    .foregroundStyle(.red)
                Spacer()
                Label(app.peerCount > 0 ? "\(app.peerCount) relay nearby" : "No relay yet",
                      systemImage: app.peerCount > 0 ? "dot.radiowaves.left.and.right" : "magnifyingglass")
                    .foregroundStyle(app.peerCount > 0 ? .green : .secondary)
            }
            .font(.footnote)

            StatusTimelineView(stage: app.sendStage)

            Spacer()

            TextField("Type a message…", text: $app.draft, axis: .vertical)
                .textFieldStyle(.roundedBorder)
                .lineLimit(1...4)

            Button {
                app.sendDraft()
            } label: {
                Label("Send via nearby relay", systemImage: "paperplane.fill")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(app.draft.trimmingCharacters(in: .whitespaces).isEmpty || app.peerCount == 0)
        }
        .padding()
        .navigationTitle("Sender")
        .navigationBarTitleDisplayMode(.inline)
    }
}
