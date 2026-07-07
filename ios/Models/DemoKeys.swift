import Foundation
import CryptoKit

/// For the demo we skip the key-exchange step (QR code / directory server) and
/// derive the recipient's keypair deterministically from a fixed seed, so the
/// sender already "knows" the recipient's public key at compile time.
///
/// ⚠️ Demo only — never ship hardcoded keys.
enum DemoKeys {
    static let recipientId = "C"


    /// The recipient ("C") private key — only the Recipient device uses this.
    static let recipientPrivateKey: Curve25519.KeyAgreement.PrivateKey = {
        let seed = SHA256.hash(data: Data("relay-demo-recipient-2025".utf8))
        return try! Curve25519.KeyAgreement.PrivateKey(rawRepresentation: Data(seed))
    }()

    /// The matching public key — the Sender encrypts to this.
    static var recipientPublicKey: Curve25519.KeyAgreement.PublicKey {
        recipientPrivateKey.publicKey
    }
}
