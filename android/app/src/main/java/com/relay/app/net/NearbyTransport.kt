package com.relay.app.net

import android.content.Context
import android.util.Log
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.AdvertisingOptions
import com.google.android.gms.nearby.connection.ConnectionInfo
import com.google.android.gms.nearby.connection.ConnectionLifecycleCallback
import com.google.android.gms.nearby.connection.ConnectionResolution
import com.google.android.gms.nearby.connection.DiscoveredEndpointInfo
import com.google.android.gms.nearby.connection.DiscoveryOptions
import com.google.android.gms.nearby.connection.EndpointDiscoveryCallback
import com.google.android.gms.nearby.connection.Payload
import com.google.android.gms.nearby.connection.PayloadCallback
import com.google.android.gms.nearby.connection.PayloadTransferUpdate
import com.google.android.gms.nearby.connection.Strategy

/// The relay ADVERTISES ("I can relay to the internet"); the sender DISCOVERS and
/// initiates the connection. Asymmetric on purpose: if both sides advertised AND
/// discovered, they'd both call requestConnection and race — the classic Nearby
/// flake. With one initiator there's no race. Once connected the link is
/// bidirectional (relay can send ACKs back).
enum class TransportMode { ADVERTISE, DISCOVER }

class NearbyTransport(
    context: Context,
    private val nickname: String,
    private val mode: TransportMode,
) {
    private val tag = "NearbyTransport"
    private val serviceId = "com.relay.app.SERVICE"
    private val strategy = Strategy.P2P_CLUSTER
    private val client = Nearby.getConnectionsClient(context)

    private val connected = mutableSetOf<String>()

    var onReceive: ((ByteArray) -> Unit)? = null
    var onPeersChanged: ((Int) -> Unit)? = null

    private val payloadCallback = object : PayloadCallback() {
        override fun onPayloadReceived(endpointId: String, payload: Payload) {
            payload.asBytes()?.let { onReceive?.invoke(it) }
        }
        override fun onPayloadTransferUpdate(endpointId: String, update: PayloadTransferUpdate) {}
    }

    private val lifecycleCallback = object : ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(endpointId: String, info: ConnectionInfo) {
            client.acceptConnection(endpointId, payloadCallback)   // auto-accept for the demo
        }
        override fun onConnectionResult(endpointId: String, result: ConnectionResolution) {
            if (result.status.isSuccess) {
                connected.add(endpointId)
                onPeersChanged?.invoke(connected.size)
            } else {
                Log.w(tag, "connection to $endpointId failed: ${result.status.statusMessage}")
            }
        }
        override fun onDisconnected(endpointId: String) {
            connected.remove(endpointId)
            onPeersChanged?.invoke(connected.size)
        }
    }

    private val discoveryCallback = object : EndpointDiscoveryCallback() {
        override fun onEndpointFound(endpointId: String, info: DiscoveredEndpointInfo) {
            client.requestConnection(nickname, endpointId, lifecycleCallback)
                .addOnFailureListener { Log.w(tag, "requestConnection failed", it) }
        }
        override fun onEndpointLost(endpointId: String) {}
    }

    fun start() {
        when (mode) {
            TransportMode.ADVERTISE -> client.startAdvertising(
                nickname, serviceId, lifecycleCallback,
                AdvertisingOptions.Builder().setStrategy(strategy).build()
            ).addOnFailureListener { Log.w(tag, "startAdvertising failed", it) }

            TransportMode.DISCOVER -> client.startDiscovery(
                serviceId, discoveryCallback,
                DiscoveryOptions.Builder().setStrategy(strategy).build()
            ).addOnFailureListener { Log.w(tag, "startDiscovery failed", it) }
        }
    }

    fun stop() {
        client.stopAdvertising()
        client.stopDiscovery()
        client.stopAllEndpoints()
        connected.clear()
    }

    /// Returns false if no peer is connected yet.
    fun send(bytes: ByteArray): Boolean {
        if (connected.isEmpty()) return false
        val payload = Payload.fromBytes(bytes)
        connected.forEach { client.sendPayload(it, payload) }
        return true
    }
}
