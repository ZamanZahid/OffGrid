package com.relay.app.net

import com.relay.app.model.Envelope
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

/// The cloud hop. Relay `upload`s; recipient `startListening`s (polls).
/// Swap this for a Firestore/WebSocket implementation without touching the UI.
interface MessageBackend {
    suspend fun upload(envelope: Envelope)
    fun startListening(recipientId: String, scope: CoroutineScope, onMessage: (Envelope) -> Unit)
    fun stopListening()
}

class RestBackend(private val baseUrl: String) : MessageBackend {

    private val client = OkHttpClient()
    private val json = Json { ignoreUnknownKeys = true }
    private val jsonMedia = "application/json".toMediaType()
    private var pollJob: Job? = null
    private val seen = mutableSetOf<String>()

    override suspend fun upload(envelope: Envelope) = withContext(Dispatchers.IO) {
        val body = json.encodeToString(Envelope.serializer(), envelope).toRequestBody(jsonMedia)
        val req = Request.Builder().url("$baseUrl/send").post(body).build()
        client.newCall(req).execute().use { /* ignore response body */ }
        Unit
    }

    override fun startListening(recipientId: String, scope: CoroutineScope, onMessage: (Envelope) -> Unit) {
        pollJob = scope.launch(Dispatchers.IO) {
            while (isActive) {
                try {
                    val req = Request.Builder()
                        .url("$baseUrl/messages?recipient=$recipientId")
                        .get().build()
                    client.newCall(req).execute().use { resp ->
                        val text = resp.body?.string() ?: "[]"
                        val list = json.decodeFromString(ListSerializer(Envelope.serializer()), text)
                        for (env in list) {
                            if (seen.add(env.id)) {
                                withContext(Dispatchers.Main) { onMessage(env) }
                            }
                        }
                    }
                } catch (e: Exception) {
                    // ignore transient network / parse errors during the demo
                }
                delay(1500)
            }
        }
    }

    override fun stopListening() {
        pollJob?.cancel()
        pollJob = null
    }
}
