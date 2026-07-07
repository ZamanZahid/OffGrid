package com.aerogaze.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.aerogaze.app.ui.ConstellationBackground
import com.aerogaze.app.ui.ConstellationTheme
import com.relay.app.ui.RelayRoot

/**
 * Merged host. A two-page swipe pager with a shared constellation look:
 *   page 0 = Relay   (Compose - offline message relay, all three roles)
 *   page 1 = Skygaze (Compose - on-device star positioning)
 * Swipe left → Skygaze, swipe right → Relay.
 */
class MainActivity : ComponentActivity() {

    private val requiredPermissions: Array<String>
        get() {
            val list = mutableListOf<String>()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                list += Manifest.permission.BLUETOOTH_ADVERTISE
                list += Manifest.permission.BLUETOOTH_CONNECT
                list += Manifest.permission.BLUETOOTH_SCAN
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                list += Manifest.permission.NEARBY_WIFI_DEVICES
            } else {
                list += Manifest.permission.ACCESS_FINE_LOCATION
            }
            return list.toTypedArray()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { /* Relay just won't connect if denied; grant for the demo */ }
            .launch(requiredPermissions)

        setContent { MergedRoot() }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun MergedRoot() {
    val pager = rememberPagerState(pageCount = { 2 })
    // One shared backdrop behind BOTH pages, so the sky stays continuous while you swipe.
    ConstellationTheme {
        ConstellationBackground {
            HorizontalPager(state = pager, modifier = Modifier.fillMaxSize()) { page ->
                when (page) {
                    0 -> RelayRoot()
                    else -> SkygazeScreen()
                }
            }
        }
    }
}
