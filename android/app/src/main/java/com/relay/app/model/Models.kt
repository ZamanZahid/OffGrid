package com.relay.app.model

import kotlinx.serialization.Serializable

/// What travels  A → relay → cloud → recipient. Binary fields are base64 so the
/// JSON is identical to what the Python server stores and returns.
@Serializable
data class Envelope(
    val id: String,                 // UUID string
    val recipientId: String,
    val ciphertext: String,         // base64( iv(12) + AES-GCM ciphertext+tag )
    val ephemeralPublicKey: String, // base64( raw X25519 public key, 32 bytes )
    val createdAt: String           // epoch millis as string
)

/// Sent back by the relay over Bluetooth once the cloud upload succeeds —
/// that's how the offline sender reaches "Delivered ✓".
@Serializable
data class Ack(val ackId: String)
