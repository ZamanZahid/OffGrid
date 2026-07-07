package com.relay.app.ui

import androidx.compose.runtime.Composable
import com.aerogaze.app.ui.ConstellationTheme

/** Relay uses the shared constellation theme so both halves of the app match. */
@Composable
fun RelayTheme(content: @Composable () -> Unit) = ConstellationTheme(content)
