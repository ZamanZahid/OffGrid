import SwiftUI

enum Role: String, CaseIterable, Identifiable {
    case sender    = "Sender (offline)"
    case relay     = "Relay (online)"
    case recipient = "Recipient"
    var id: String { rawValue }

    var icon: String {
        switch self {
        case .sender:    return "paperplane.fill"
        case .relay:     return "antenna.radiowaves.left.and.right"
        case .recipient: return "tray.and.arrow.down.fill"
        }
    }
}

/// The sender's status timeline. Order matters — see StatusTimelineView.
enum SendStage: String {
    case searching  = "Searching for a nearby relay…"
    case relayFound = "Relay found nearby"
    case sent       = "Handed to relay over Bluetooth"
    case delivered  = "Delivered ✓"
}

/// Single source of truth. One app, three roles — pick one per device.
final class AppModel: ObservableObject {

    // 🔧 CHANGE THIS to your server machine's LAN IP (or ngrok URL).
    //    Find it on the laptop running server.py:  macOS → System Settings ▸ Wi-Fi ▸ Details.
    private let serverURL = URL(string: "http://192.168.1.50:8080")!

    @Published var role: Role?
    @Published var peerCount: Int = 0

    // Sender
    @Published var draft: String = ""
    @Published var sendStage: SendStage = .searching

    // Relay — what passed through this phone (encrypted!)
    @Published var relayLog: [RelayLogEntry] = []

    // Recipient — decrypted inbox
    @Published var inbox: [InboxMessage] = []

    private var mpc: MultipeerSession?
    private var backend: MessageBackend?

    // MARK: - Role selection

    func choose(role: Role) {
        self.role = role
        switch role {
        case .sender:
            let mpc = MultipeerSession(displayName: "A-sender")
            mpc.onPeersChanged = { [weak self] peers in self?.handlePeers(peers.count) }
            mpc.onReceive = { [weak self] data, _ in self?.senderReceived(data) }
            self.mpc = mpc
            sendStage = .searching
            mpc.start()

        case .relay:
            let mpc = MultipeerSession(displayName: "B-relay")
            mpc.onPeersChanged = { [weak self] peers in self?.peerCount = peers.count }
            mpc.onReceive = { [weak self] data, _ in self?.relayReceived(data) }
            self.mpc = mpc
            self.backend = RESTBackend(baseURL: serverURL)
            mpc.start()

        case .recipient:
            let backend = RESTBackend(baseURL: serverURL)
            self.backend = backend
            backend.startListening(recipientId: DemoKeys.recipientId) { [weak self] env in
                self?.recipientReceived(env)
            }
        }
    }

    // MARK: - Sender

    func sendDraft() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, let mpc else { return }
        do {
            let env = try RelayCrypto.seal(text,
                                           to: DemoKeys.recipientPublicKey,
                                           recipientId: DemoKeys.recipientId)
            let data = try JSONEncoder.relay.encode(env)
            if mpc.send(data) {
                sendStage = .sent
                draft = ""
            } else {
                sendStage = .searching
            }
        } catch {
            print("seal/send error:", error)
        }
    }

    private func senderReceived(_ data: Data) {
        // The only thing the relay sends back is an ACK.
        if (try? JSONDecoder.relay.decode(Ack.self, from: data)) != nil {
            sendStage = .delivered
        }
    }

    private func handlePeers(_ count: Int) {
        peerCount = count
        if role == .sender, sendStage != .sent, sendStage != .delivered {
            sendStage = count > 0 ? .relayFound : .searching
        }
    }

    // MARK: - Relay

    private func relayReceived(_ data: Data) {
        guard let env = try? JSONDecoder.relay.decode(Envelope.self, from: data) else { return }
        let preview = String(env.ciphertext.base64EncodedString().prefix(28)) + "…"
        relayLog.insert(RelayLogEntry(id: env.id,
                                      recipient: env.recipientId,
                                      ciphertextPreview: preview,
                                      status: "uploading…"), at: 0)
        Task {
            do {
                try await backend?.upload(env)
                await MainActor.run {
                    self.updateRelay(env.id, status: "delivered to cloud ✓")
                    // Tell the offline sender it landed.
                    if let ack = try? JSONEncoder.relay.encode(Ack(ackId: env.id)) {
                        self.mpc?.send(ack)
                    }
                }
            } catch {
                await MainActor.run { self.updateRelay(env.id, status: "upload failed") }
            }
        }
    }

    private func updateRelay(_ id: UUID, status: String) {
        if let i = relayLog.firstIndex(where: { $0.id == id }) {
            relayLog[i].status = status
        }
    }

    // MARK: - Recipient

    private func recipientReceived(_ env: Envelope) {
        let text = (try? RelayCrypto.open(env, with: DemoKeys.recipientPrivateKey))
            ?? "⚠️ could not decrypt"
        guard !inbox.contains(where: { $0.id == env.id }) else { return }
        inbox.insert(InboxMessage(id: env.id, text: text, at: env.createdAt), at: 0)
    }
}

struct RelayLogEntry: Identifiable {
    let id: UUID
    let recipient: String
    let ciphertextPreview: String
    var status: String
}

struct InboxMessage: Identifiable {
    let id: UUID
    let text: String
    let at: Date
}
