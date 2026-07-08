import Foundation
import CryptoKit

/// End-to-end encryption (ECIES-style): X25519 key agreement → HKDF → ChaChaPoly.
/// This is the whole privacy story — the relay only ever holds `ciphertext`.
enum RelayCrypto {

    private static let salt = Data("relay-demo-salt".utf8)

    /// SENDER side: encrypt `text` so ONLY the holder of `recipientPublicKey`
    /// can read it. Uses a fresh ephemeral key per message (forward secrecy-ish).
    static func seal(_ text: String,
                     to recipientPublicKey: Curve25519.KeyAgreement.PublicKey,
                     recipientId: String) throws -> Envelope {
        let ephemeral = Curve25519.KeyAgreement.PrivateKey()
        let shared = try ephemeral.sharedSecretFromKeyAgreement(with: recipientPublicKey)
        let key = shared.hkdfDerivedSymmetricKey(using: SHA256.self,
                                                 salt: salt,
                                                 sharedInfo: Data(),
                                                 outputByteCount: 32)
        let sealed = try ChaChaPoly.seal(Data(text.utf8), using: key)
        return Envelope(recipientId: recipientId,
                        ciphertext: sealed.combined,
                        ephemeralPublicKey: ephemeral.publicKey.rawRepresentation)
    }

    /// RECIPIENT side: derive the same key from the ephemeral public key +
    /// our private key, then open the box.
    static func open(_ envelope: Envelope,
                     with recipientPrivateKey: Curve25519.KeyAgreement.PrivateKey) throws -> String {
        let ephemeralPub = try Curve25519.KeyAgreement.PublicKey(
            rawRepresentation: envelope.ephemeralPublicKey)
        let shared = try recipientPrivateKey.sharedSecretFromKeyAgreement(with: ephemeralPub)
        let key = shared.hkdfDerivedSymmetricKey(using: SHA256.self,
                                                 salt: salt,
                                                 sharedInfo: Data(),
                                                 outputByteCount: 32)
        let box = try ChaChaPoly.SealedBox(combined: envelope.ciphertext)
        let plain = try ChaChaPoly.open(box, using: key)
        return String(decoding: plain, as: UTF8.self)
    }
}
