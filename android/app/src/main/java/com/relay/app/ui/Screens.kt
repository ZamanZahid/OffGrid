@file:OptIn(ExperimentalMaterial3Api::class)

package com.relay.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.relay.app.AppViewModel
import com.relay.app.Role
import com.relay.app.SendStage
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun RelayRoot(vm: AppViewModel = viewModel()) {
    when (vm.role) {
        null -> RoleSelectionScreen(vm)
        Role.SENDER -> SenderScreen(vm)
        Role.RELAY -> RelayScreen(vm)
        Role.RECIPIENT -> RecipientScreen(vm)
    }
}

@Composable
private fun RoleSelectionScreen(vm: AppViewModel) {
    Column(
        modifier = Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text("📡", fontSize = 56.sp)
        Text("Relay", style = MaterialTheme.typography.headlineLarge)
        Text("Find My, but for messages.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(28.dp))
        OutlinedTextField(
            value = vm.serverUrl,
            onValueChange = { vm.serverUrl = it },
            label = { Text("Server URL (relay & recipient)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(Modifier.height(20.dp))
        Text("Pick this device's role", style = MaterialTheme.typography.labelMedium)
        Spacer(Modifier.height(12.dp))
        Role.entries.forEach { role ->
            Button(
                onClick = { vm.choose(role) },
                modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)
            ) { Text(role.label) }
        }
    }
}

@Composable
private fun SenderScreen(vm: AppViewModel) {
    Scaffold(topBar = {
        TopAppBar(
            title = { Text("Sender") },
            navigationIcon = { TextButton(onClick = { vm.reset() }) { Text("‹ Role") } }
        )
    }) { pad ->
        Column(Modifier.padding(pad).padding(16.dp).fillMaxSize()) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("🔴 No internet", color = MaterialTheme.colorScheme.error)
                Text(if (vm.peerCount > 0) "🟢 ${vm.peerCount} relay nearby" else "🔍 No relay yet")
            }
            Spacer(Modifier.height(16.dp))
            StatusTimeline(vm.sendStage)
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(
                value = vm.draft,
                onValueChange = { vm.draft = it },
                label = { Text("Type a message…") },
                modifier = Modifier.fillMaxWidth()
            )
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = { vm.send() },
                enabled = vm.draft.isNotBlank() && vm.peerCount > 0,
                modifier = Modifier.fillMaxWidth()
            ) { Text("Send via nearby relay") }
        }
    }
}

@Composable
private fun StatusTimeline(stage: SendStage) {
    val steps = listOf(SendStage.SEARCHING, SendStage.RELAY_FOUND, SendStage.SENT, SendStage.DELIVERED)
    val currentIndex = steps.indexOf(stage)
    Column(
        Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(16.dp)
    ) {
        steps.forEachIndexed { i, s ->
            val reached = i <= currentIndex
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(vertical = 6.dp)
            ) {
                Text(if (reached) "✅" else "⬜")
                Spacer(Modifier.width(10.dp))
                Text(
                    s.label,
                    color = if (reached) MaterialTheme.colorScheme.onSurface
                    else MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun RelayScreen(vm: AppViewModel) {
    Scaffold(topBar = {
        TopAppBar(
            title = { Text("Relay") },
            navigationIcon = { TextButton(onClick = { vm.reset() }) { Text("‹ Role") } }
        )
    }) { pad ->
        Column(Modifier.padding(pad).padding(16.dp).fillMaxSize()) {
            Text(
                if (vm.peerCount > 0) "🟢 ${vm.peerCount} device(s) connected"
                else "🔍 Waiting for nearby devices…"
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "This phone carries other people's messages to the internet. It only ever sees ciphertext 🔒 — it can't read any of them.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(Modifier.height(12.dp))
            if (vm.relayLog.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Nothing relayed yet 🔒")
                }
            } else {
                LazyColumn(Modifier.fillMaxSize()) {
                    items(vm.relayLog) { e ->
                        Column(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                            Text(
                                "→ recipient ${e.recipient}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                e.preview,
                                fontFamily = FontFamily.Monospace,
                                maxLines = 1,
                                color = Color(0xFFCC7722)
                            )
                            Text(
                                e.status,
                                style = MaterialTheme.typography.labelSmall,
                                color = if (e.status.contains("✓")) Color(0xFF2E7D32)
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

@Composable
private fun RecipientScreen(vm: AppViewModel) {
    Scaffold(topBar = {
        TopAppBar(
            title = { Text("Recipient") },
            navigationIcon = { TextButton(onClick = { vm.reset() }) { Text("‹ Role") } }
        )
    }) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            if (vm.inbox.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("📭 Waiting for messages…")
                }
            } else {
                LazyColumn(Modifier.fillMaxSize().padding(16.dp)) {
                    items(vm.inbox) { m ->
                        Column(Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                            Text(m.text, style = MaterialTheme.typography.bodyLarge)
                            Text(
                                formatTime(m.atMillis),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        HorizontalDivider()
                    }
                }
            }
        }
    }
}

private fun formatTime(millis: Long): String =
    SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(millis))
