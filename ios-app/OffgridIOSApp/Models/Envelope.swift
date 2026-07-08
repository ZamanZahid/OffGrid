import Foundation

/// What actually travels  A → relay → cloud → recipient.
/// The relay and the server can read `recipientId` and timestamps, but the
/// message body lives in `ciphertext`, sealed to the recipient's key — so a
/// relaying stranger (and our own server) can never read it.
struct Envelope: Codable, Identifiable {
    let id: UUID
    let recipientId: String
    let ciphertext: Data          // ChaChaPoly sealed box (.combined)
    let ephemeralPublicKey: Data  // sender's one-time X25519 public key
    let createdAt: Date

    init(id: UUID = UUID(),
         recipientId: String,
         ciphertext: Data,
         ephemeralPublicKey: Data,
         createdAt: Date = Date()) {
        self.id = id
        self.recipientId = recipientId
        self.ciphertext = ciphertext
        self.ephemeralPublicKey = ephemeralPublicKey
        self.createdAt = createdAt
    }
}

/// Tiny acknowledgement the relay sends back to the (offline) sender over
/// Bluetooth once the cloud upload succeeds — that's how an offline phone gets
/// to show "Delivered ✓".
struct Ack: Codable {
    let ackId: UUID
}

/// Shared JSON coders so dates/Data encode identically on every device.
extension JSONEncoder {
    static let relay: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}
extension JSONDecoder {
    static let relay: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}
