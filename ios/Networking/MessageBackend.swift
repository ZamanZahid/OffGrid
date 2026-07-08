import Foundation

/// The cloud hop. The relay `upload`s; the recipient `startListening`s.
/// Swap RESTBackend for a Firestore/Supabase implementation without touching
/// the rest of the app.
protocol MessageBackend {
    /// Relay → cloud.
    func upload(_ envelope: Envelope) async throws
    /// Recipient ← cloud. `onMessage` is invoked on the main thread.
    func startListening(recipientId: String, onMessage: @escaping (Envelope) -> Void)
    func stopListening()
}

