package com.relay.app

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.relay.app.crypto.DemoKeys
import com.relay.app.crypto.RelayCrypto
import com.relay.app.model.Ack
import com.relay.app.model.Envelope
import com.relay.app.net.MessageBackend
import com.relay.app.net.NearbyTransport
import com.relay.app.net.RestBackend
import com.relay.app.net.TransportMode
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

enum class Role(val label: String) {
    SENDER("Sender (offline)"),
    RELAY("Relay (online)"),
    RECIPIENT("Recipient")
}

enum class SendStage(val label: String) {
    SEARCHING("Searching for a nearby relay…"),
    RELAY_FOUND("Relay found nearby"),
    SENT("Handed to relay over Bluetooth"),
    DELIVERED("Delivered ✓")
}

data class RelayLogEntry(val id: String, val recipient: String, val preview: String, val status: String)
data class InboxMessage(val id: String, val text: String, val atMillis: Long)

class AppViewModel(app: Application) : AndroidViewModel(app) {

    // Editable on the role-selection screen, so you can fix the IP at the venue
    // without rebuilding. Default = this machine's current LAN IP.
    var serverUrl by mutableStateOf("http://192.168.0.164:8080")

    private val json = Json { ignoreUnknownKeys = true }

    var role by mutableStateOf<Role?>(null); private set
    var peerCount by mutableStateOf(0); private set
    var draft by mutableStateOf("")
    var sendStage by mutableStateOf(SendStage.SEARCHING); private set

    val relayLog = mutableStateListOf<RelayLogEntry>()
    val inbox = mutableStateListOf<InboxMessage>()

    private var transport: NearbyTransport? = null
    private var backend: MessageBackend? = null

    fun choose(role: Role) {
        this.role = role
        when (role) {
            Role.SENDER -> {
                val t = NearbyTransport(getApplication(), "A-sender", TransportMode.DISCOVER)
                t.onPeersChanged = { count ->
                    peerCount = count
                    if (sendStage != SendStage.SENT && sendStage != SendStage.DELIVERED) {
                        sendStage = if (count > 0) SendStage.RELAY_FOUND else SendStage.SEARCHING
                    }
                }
                t.onReceive = { data -> onSenderReceive(data) }
                transport = t
                sendStage = SendStage.SEARCHING
                t.start()
            }
            Role.RELAY -> {
                val t = NearbyTransport(getApplication(), "B-relay", TransportMode.ADVERTISE)
                t.onPeersChanged = { count -> peerCount = count }
                t.onReceive = { data -> onRelayReceive(data) }
                transport = t
                backend = RestBackend(serverUrl)
                t.start()
            }
            Role.RECIPIENT -> {
                val b = RestBackend(serverUrl)
                backend = b
                b.startListening(DemoKeys.recipientId, viewModelScope) { env -> onRecipientReceive(env) }
            }
        }
    }

    // MARK: Sender
    fun send() {
        val text = draft.trim()
        val t = transport ?: return
        if (text.isEmpty()) return
        val env = RelayCrypto.seal(text, DemoKeys.recipientPublic, DemoKeys.recipientId)
        val bytes = json.encodeToString(Envelope.serializer(), env).toByteArray()
        if (t.send(bytes)) {
            sendStage = SendStage.SENT
            draft = ""
        } else {
            sendStage = SendStage.SEARCHING
        }
    }

    private fun onSenderReceive(data: ByteArray) {
        try {
            json.decodeFromString(Ack.serializer(), String(data))
            sendStage = SendStage.DELIVERED   // the relay confirmed the cloud upload
        } catch (e: Exception) {
            // not an ack; ignore
        }
    }

    // MARK: Relay
    private fun onRelayReceive(data: ByteArray) {
        val env = try {
            json.decodeFromString(Envelope.serializer(), String(data))
        } catch (e: Exception) {
            return
        }
        val preview = env.ciphertext.take(28) + "…"
        relayLog.add(0, RelayLogEntry(env.id, env.recipientId, preview, "uploading…"))
        viewModelScope.launch {
            try {
                backend?.upload(env)
                updateRelay(env.id, "delivered to cloud ✓")
                // Tell the offline sender it landed.
                val ack = json.encodeToString(Ack.serializer(), Ack(env.id)).toByteArray()
                transport?.send(ack)
            } catch (e: Exception) {
                updateRelay(env.id, "upload failed: ${e.message ?: e.javaClass.simpleName}")
            }
        }
    }

    private fun updateRelay(id: String, status: String) {
        val i = relayLog.indexOfFirst { it.id == id }
        if (i >= 0) relayLog[i] = relayLog[i].copy(status = status)
    }

    // MARK: Recipient
    private fun onRecipientReceive(env: Envelope) {
        if (inbox.any { it.id == env.id }) return
        val text = try {
            RelayCrypto.open(env, DemoKeys.recipientPrivate)
        } catch (e: Exception) {
            "⚠️ could not decrypt"
        }
        val millis = env.createdAt.toLongOrNull() ?: System.currentTimeMillis()
        inbox.add(0, InboxMessage(env.id, text, millis))
    }

    /// Return to the role picker — lets one phone switch roles mid-demo
    /// (e.g. act as the Relay, then become the Recipient to decrypt what it relayed).
    fun reset() {
        transport?.stop()
        backend?.stopListening()
        transport = null
        backend = null
        role = null
        peerCount = 0
        sendStage = SendStage.SEARCHING
        draft = ""
        relayLog.clear()
        inbox.clear()
    }

    override fun onCleared() {
        transport?.stop()
        backend?.stopListening()
    }
}
