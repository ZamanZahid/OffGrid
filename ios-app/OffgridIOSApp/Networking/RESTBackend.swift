import Foundation

/// Talks to the zero-dependency server in /server/server.py.
///   • Relay     POSTs   /send
///   • Recipient polls   GET /messages?recipient=C   (every 1.5s)
///
/// Polling is intentionally dumb — it's bulletproof for a live demo. Realtime
/// (Firestore listener / WebSocket) is a one-file swap if you want it.
final class RESTBackend: MessageBackend {

    private let baseURL: URL
    private let candidateURLs: [URL]
    private var activeBaseURL: URL
    private var pollTask: Task<Void, Never>?
    private var seenIDs = Set<UUID>()

    init(baseURL: URL) {
        self.baseURL = baseURL
        self.candidateURLs = [baseURL] + ServerConfig.fallbackURLs.filter { $0 != baseURL }
        self.activeBaseURL = baseURL
    }

    func upload(_ envelope: Envelope) async throws {
        var lastError: Error?

        for candidate in candidateURLs {
            let url = candidate.appendingPathComponent("send")
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONEncoder.relay.encode(envelope)
            req.timeoutInterval = 8

            do {
                let (_, response) = try await URLSession.shared.data(for: req)
                guard let http = response as? HTTPURLResponse else {
                    throw URLError(.badServerResponse)
                }
                guard (200...299).contains(http.statusCode) else {
                    throw URLError(.badServerResponse)
                }

                activeBaseURL = candidate
                return
            } catch {
                lastError = error
                if let urlError = error as? URLError, urlError.code == .timedOut {
                    continue
                }
            }
        }

        throw lastError ?? URLError(.badServerResponse)
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
            let base = activeBaseURL
            var comps = URLComponents(url: base.appendingPathComponent("messages"),
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
            // A short-lived timeout on startup is common; the next poll will retry.
        }
    }
}
