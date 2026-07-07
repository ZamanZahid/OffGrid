package com.relay.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aerogaze.app.ui.AccentCyan
import com.aerogaze.app.ui.AccentGold
import com.aerogaze.app.ui.GlassBg
import com.aerogaze.app.ui.GlassBorder
import com.aerogaze.app.ui.GlassCard
import com.aerogaze.app.ui.GlowButton
import com.aerogaze.app.ui.Overline
import com.aerogaze.app.ui.TextPrimary
import com.aerogaze.app.ui.TextSecondary
import com.relay.app.AppViewModel
import com.relay.app.Role
import com.relay.app.SendStage
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// Screens are transparent; the shared ConstellationBackground (in MainActivity) shows
// through so the sky stays continuous while swiping between pages.

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
private fun ScreenHeader(title: String, onBack: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("‹ Role", color = AccentCyan, fontSize = 14.sp,
            modifier = Modifier.clickable { onBack() })
        Spacer(Modifier.width(14.dp))
        Text(title, color = TextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun RoleSelectionScreen(vm: AppViewModel) {
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(48.dp))
        Text("✦", color = AccentGold, fontSize = 40.sp)
        Text("Relay", color = TextPrimary, fontSize = 34.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(28.dp))

        OutlinedTextField(
            value = vm.serverUrl,
            onValueChange = { vm.serverUrl = it },
            label = { Text("Server URL (relay & recipient)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(22.dp))
        Overline("Pick this device's role")
        Spacer(Modifier.height(10.dp))

        RoleButton(Role.SENDER, "Send a message with no signal", "📡") { vm.choose(Role.SENDER) }
        Spacer(Modifier.height(10.dp))
        RoleButton(Role.RELAY, "Carry a nearby message to the cloud", "🛰") { vm.choose(Role.RELAY) }
        Spacer(Modifier.height(10.dp))
        RoleButton(Role.RECIPIENT, "Receive & decrypt incoming messages", "✉") { vm.choose(Role.RECIPIENT) }
    }
}

@Composable
private fun RoleButton(role: Role, desc: String, emoji: String, onClick: () -> Unit) {
    Box(
        Modifier.fillMaxWidth()
            .clip(RoundedCornerShape(3.dp))
            .background(GlassBg)
            .border(1.dp, GlassBorder, RoundedCornerShape(3.dp))
            .clickable { onClick() }
            .padding(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(emoji, fontSize = 24.sp)
            Spacer(Modifier.width(14.dp))
            Column {
                Text(role.label, color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                Text(desc, color = TextSecondary, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun SenderScreen(vm: AppViewModel) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        ScreenHeader("Sender") { vm.reset() }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text("🔴 No internet", color = Color(0xFFFF8A8A), fontSize = 13.sp)
            Text(
                if (vm.peerCount > 0) "🟢 ${vm.peerCount} relay nearby" else "🔍 No relay yet",
                color = if (vm.peerCount > 0) AccentCyan else TextSecondary, fontSize = 13.sp,
            )
        }
        Spacer(Modifier.height(16.dp))
        GlassCard(Modifier.fillMaxWidth()) { StatusTimeline(vm.sendStage) }
        Spacer(Modifier.weight(1f))
        OutlinedTextField(
            value = vm.draft,
            onValueChange = { vm.draft = it },
            label = { Text("Type a message…") },
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(12.dp))
        GlowButton(
            "Send via nearby relay", { vm.send() },
            Modifier.fillMaxWidth(),
            enabled = vm.draft.isNotBlank() && vm.peerCount > 0,
        )
    }
}

@Composable
private fun StatusTimeline(stage: SendStage) {
    val steps = listOf(SendStage.SEARCHING, SendStage.RELAY_FOUND, SendStage.SENT, SendStage.DELIVERED)
    val current = steps.indexOf(stage)
    Column {
        steps.forEachIndexed { i, s ->
            val reached = i <= current
            Row(Modifier.padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(if (reached) "✦" else "·", color = if (reached) AccentGold else TextSecondary, fontSize = 18.sp)
                Spacer(Modifier.width(12.dp))
                Text(s.label, color = if (reached) TextPrimary else TextSecondary, fontSize = 14.sp)
            }
        }
    }
}

@Composable
private fun RelayScreen(vm: AppViewModel) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        ScreenHeader("Relay") { vm.reset() }
        Text(
            if (vm.peerCount > 0) "🟢 ${vm.peerCount} device(s) connected" else "🔍 Waiting for nearby devices…",
            color = if (vm.peerCount > 0) AccentCyan else TextSecondary, fontSize = 13.sp,
        )
        Spacer(Modifier.height(8.dp))
        Text(
            "This phone carries other people's messages to the internet. It only ever sees ciphertext 🔒, it can't read any of them.",
            color = TextSecondary, fontSize = 12.sp,
        )
        Spacer(Modifier.height(14.dp))
        if (vm.relayLog.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Nothing relayed yet 🔒", color = TextSecondary)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(vm.relayLog) { e ->
                    GlassCard(Modifier.fillMaxWidth()) {
                        Column {
                            Text("→ recipient ${e.recipient}", color = TextSecondary, fontSize = 11.sp)
                            Text(e.preview, color = AccentGold, fontFamily = FontFamily.Monospace,
                                fontSize = 13.sp, maxLines = 1)
                            Text(e.status, color = if (e.status.contains("✓")) AccentCyan else TextSecondary,
                                fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RecipientScreen(vm: AppViewModel) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        ScreenHeader("Recipient") { vm.reset() }
        if (vm.inbox.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("📭 Waiting for messages…", color = TextSecondary)
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(vm.inbox) { m ->
                    GlassCard(Modifier.fillMaxWidth()) {
                        Column {
                            Text(m.text, color = TextPrimary, fontSize = 16.sp)
                            Text(formatTime(m.atMillis), color = TextSecondary, fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

private fun formatTime(millis: Long): String =
    SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(millis))
