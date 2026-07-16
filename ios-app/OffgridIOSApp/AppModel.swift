import SwiftUI

enum Role: String, CaseIterable, Identifiable {
    case sender
    case relay
    case recipient

    var id: String { rawValue }

    var title: String {
        switch self {
        case .sender: return "Sender"
        case .relay: return "Relay"
        case .recipient: return "Recipient"
        }
    }

    var subtitle: String {
        switch self {
        case .sender: return "Send messages without internet"
        case .relay: return "Bridge nearby phones to the cloud\n(like how find my works)"
        case .recipient: return "Receive decrypted messages"
        }
    }

    var icon: String {
        switch self {
        case .sender: return "paperplane.fill"
        case .relay: return "antenna.radiowaves.left.and.right"
        case .recipient: return "tray.and.arrow.down.fill"
        }
    }

    var defaultTab: AppTab {
        switch self {
        case .sender: return .send
        case .relay: return .relay
        case .recipient: return .inbox
        }
    }

    var visibleTabs: [AppTab] {
        switch self {
        case .sender: return [.send, .skygaze]
        case .relay: return [.relay, .skygaze]
        case .recipient: return [.inbox, .skygaze]
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

    @Published var role: Role?
    @Published var selectedTab: AppTab = .send
    @Published var peerCount: Int = 0

    // Sender
    @Published var draft: String = ""
    @Published var sendStage: SendStage = .searching

    // Relay — what passed through this phone (encrypted!)
    @Published var relayLog: [RelayLogEntry] = []

    // Recipient — decrypted inbox
    @Published var inbox: [InboxMessage] = []
    
    // 7 days so we don't lose messages if the app is deleted
    private static let inboxRetention: TimeInterval = 7 * 24 * 60 * 60

    private var mpc: MultipeerSession?
    private var relayBackend: MessageBackend?
    private var inboxBackend: MessageBackend?
    private var inboxCleanupTask: Task<Void, Never>?

    // MARK: - Navigation

    func goHome() {
        teardown()
        role = nil
        selectedTab = .send
    }

    // MARK: - Role selection

    func choose(role: Role, tab: AppTab? = nil) {
        teardown()
        self.role = role
        selectedTab = tab ?? role.defaultTab

        startInboxPolling()

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
            self.relayBackend = RESTBackend(baseURL: ServerConfig.baseURL)
            mpc.start()

        case .recipient:
            peerCount = 0
        }
    }

    func enterSkygaze() {
        choose(role: .sender, tab: .skygaze)
    }

    private func teardown() {
        mpc?.stop()
        mpc = nil
        relayBackend = nil
        inboxBackend?.stopListening()
        inboxBackend = nil
        inboxCleanupTask?.cancel()
        inboxCleanupTask = nil
        peerCount = 0
    }

    private func startInboxPolling() {
        purgeExpiredInboxMessages()
        startInboxCleanup()

        let backend = RESTBackend(baseURL: ServerConfig.baseURL)
        inboxBackend = backend
        backend.startListening(recipientId: DemoKeys.recipientId) { [weak self] env in
            self?.recipientReceived(env)
        }
    }

    private func startInboxCleanup() {
        inboxCleanupTask?.cancel()
        inboxCleanupTask = Task { [weak self] in
            while !Task.isCancelled {
                await MainActor.run { self?.purgeExpiredInboxMessages() }
                try? await Task.sleep(nanoseconds: 60_000_000_000)
            }
        }
    }

    private func purgeExpiredInboxMessages() {
        let cutoff = Date().addingTimeInterval(-Self.inboxRetention)
        inbox.removeAll { $0.at < cutoff }
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
                try await self.uploadWithRetry(env)
            } catch {
                await MainActor.run {
                    self.updateRelay(env.id, status: "upload failed")
                }
                if let urlError = error as? URLError {
                    print("Relay upload network error:", urlError.code, urlError.localizedDescription)
                    print("  URL attempted:", urlError.failingURL?.absoluteString ?? "unknown")
                    print("  Server:", ServerConfig.baseURLString)
                } else {
                    print("Relay upload error:", error)
                }
            }
        }
    }

    private func uploadWithRetry(_ env: Envelope) async throws {
        guard let relayBackend else {
            throw URLError(.unknown)
        }

        let maxAttempts = 8
        var lastError: Error?

        for attempt in 1...maxAttempts {
            do {
                try await relayBackend.upload(env)
                await MainActor.run {
                    self.updateRelay(env.id, status: "delivered to cloud ✓")
                    if let ack = try? JSONEncoder.relay.encode(Ack(ackId: env.id)) {
                        self.mpc?.send(ack)
                    }
                }
                return
            } catch {
                lastError = error
                let status = attempt < maxAttempts ? "retrying \(attempt)/\(maxAttempts)…" : "upload failed"
                await MainActor.run {
                    self.updateRelay(env.id, status: status)
                }

                if attempt < maxAttempts {
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                }
            }
        }

        throw lastError ?? URLError(.badServerResponse)
    }

    private func updateRelay(_ id: UUID, status: String) {
        if let i = relayLog.firstIndex(where: { $0.id == id }) {
            relayLog[i].status = status
        }
    }

    // MARK: - Recipient

    private func recipientReceived(_ env: Envelope) {
        let cutoff = Date().addingTimeInterval(-Self.inboxRetention)
        guard env.createdAt >= cutoff else { return }

        let text = (try? RelayCrypto.open(env, with: DemoKeys.recipientPrivateKey))
            ?? "⚠️ could not decrypt"
        guard !inbox.contains(where: { $0.id == env.id }) else { return }
        inbox.insert(InboxMessage(id: env.id, text: text, at: env.createdAt), at: 0)
        purgeExpiredInboxMessages()
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
