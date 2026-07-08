import Foundation

/// Talks to the zero-dependency server in /server/server.py.
///   • Relay     POSTs   /send
///   • Recipient polls   GET /messages?recipient=C   (every 1.5s)
///
/// Polling is intentionally dumb — it's bulletproof for a live demo. Realtime
/// (Firestore listener / WebSocket) is a one-file swap if you want it.
final class RESTBackend: MessageBackend {

    private let baseURL: URL
    private var pollTask: Task<Void, Never>?
    private var seenIDs = Set<UUID>()

    init(baseURL: URL) {
        self.baseURL = baseURL
    }

    func upload(_ envelope: Envelope) async throws {
        var req = URLRequest(url: baseURL.appendingPathComponent("send"))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder.relay.encode(envelope)
        _ = try await URLSession.shared.data(for: req)
    }

    func startListening(recipientId: String, onMessage: @escaping (Envelope) -> Void) {
        pollTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.pollOnce(recipientId: recipientId, onMessage: onMessage)
                try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5s
            }
        }
    }

    func stopListening() {
        pollTask?.cancel()
        pollTask = nil
    }

    private func pollOnce(recipientId: String, onMessage: @escaping (Envelope) -> Void) async {
        do {
            var comps = URLComponents(url: baseURL.appendingPathComponent("messages"),
                                      resolvingAgainstBaseURL: false)!
            comps.queryItems = [URLQueryItem(name: "recipient", value: recipientId)]
            let (data, _) = try await URLSession.shared.data(from: comps.url!)
            let envelopes = try JSONDecoder.relay.decode([Envelope].self, from: data)
            for env in envelopes where !seenIDs.contains(env.id) {
                seenIDs.insert(env.id)
                await MainActor.run { onMessage(env) }
            }
        } catch {
            // Ignore transient network errors during the demo.
        }
    }
}
