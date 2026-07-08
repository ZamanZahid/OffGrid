import SwiftUI

struct RecipientView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        Group {
            if app.inbox.isEmpty {
                ContentUnavailableView("Waiting for messages",
                                       systemImage: "tray",
                                       description: Text("Messages relayed through a nearby phone will arrive here, decrypted."))
            } else {
                List(app.inbox) { msg in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(msg.text)
                            .font(.body)
                        Text(msg.at, style: .time)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 2)
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Recipient")
        .navigationBarTitleDisplayMode(.inline)
    }
}
