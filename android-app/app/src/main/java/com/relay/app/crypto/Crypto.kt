package com.relay.app.crypto

import android.util.Base64
import com.relay.app.model.Envelope
import org.bouncycastle.crypto.agreement.X25519Agreement
import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.generators.HKDFBytesGenerator
import org.bouncycastle.crypto.params.HKDFParameters
import org.bouncycastle.crypto.params.X25519PrivateKeyParameters
import org.bouncycastle.crypto.params.X25519PublicKeyParameters
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/// End-to-end encryption: X25519 ECDH → HKDF-SHA256 → AES-256-GCM.
/// The relay and the server only ever see `ciphertext` - this is the privacy story.
object RelayCrypto {

    private val salt = "relay-demo-salt".toByteArray()
    private val rng = SecureRandom()

    /// SENDER: encrypt so ONLY the holder of [recipientPub] can read it.
    fun seal(text: String, recipientPub: X25519PublicKeyParameters, recipientId: String): Envelope {
        val ephPriv = X25519PrivateKeyParameters(rng)         // fresh key per message
        val ephPub = ephPriv.generatePublicKey()

        val agreement = X25519Agreement()
        agreement.init(ephPriv)
        val shared = ByteArray(agreement.agreementSize)
        agreement.calculateAgreement(recipientPub, shared, 0)
        val key = hkdf(shared, 32)

        val iv = ByteArray(12).also { rng.nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        val combined = iv + cipher.doFinal(text.toByteArray(Charsets.UTF_8))

        return Envelope(
            id = UUID.randomUUID().toString(),
            recipientId = recipientId,
            ciphertext = Base64.encodeToString(combined, Base64.NO_WRAP),
            ephemeralPublicKey = Base64.encodeToString(ephPub.encoded, Base64.NO_WRAP),
            createdAt = System.currentTimeMillis().toString()
        )
    }

    /// RECIPIENT: re-derive the shared key from the ephemeral public key + our private key.
    fun open(env: Envelope, recipientPriv: X25519PrivateKeyParameters): String {
        val ephPub = X25519PublicKeyParameters(Base64.decode(env.ephemeralPublicKey, Base64.NO_WRAP), 0)

        val agreement = X25519Agreement()
        agreement.init(recipientPriv)
        val shared = ByteArray(agreement.agreementSize)
        agreement.calculateAgreement(ephPub, shared, 0)
        val key = hkdf(shared, 32)

        val combined = Base64.decode(env.ciphertext, Base64.NO_WRAP)
        val iv = combined.copyOfRange(0, 12)
        val ct = combined.copyOfRange(12, combined.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(128, iv))
        return String(cipher.doFinal(ct), Charsets.UTF_8)
    }

    private fun hkdf(ikm: ByteArray, len: Int): ByteArray {
        val gen = HKDFBytesGenerator(SHA256Digest())
        gen.init(HKDFParameters(ikm, salt, ByteArray(0)))
        val out = ByteArray(len)
        gen.generateBytes(out, 0, len)
        return out
    }
}

/// Demo shortcut: derive the recipient's keypair from a fixed seed so the sender
/// already "knows" the public key - skips key exchange. ⚠️ Demo only.
object DemoKeys {
    const val recipientId = "C"

    val recipientPrivate: X25519PrivateKeyParameters by lazy {
        val seed = MessageDigest.getInstance("SHA-256").digest("relay-demo-recipient-2025".toByteArray())
        X25519PrivateKeyParameters(seed, 0)
    }

    val recipientPublic: X25519PublicKeyParameters
        get() = recipientPrivate.generatePublicKey()
}
