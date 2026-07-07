package com.relay.app

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import com.relay.app.ui.RelayRoot
import com.relay.app.ui.RelayTheme

class MainActivity : ComponentActivity() {

    /// Nearby Connections needs different runtime permissions per Android version.
    private val requiredPermissions: Array<String>
        get() {
            val list = mutableListOf<String>()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {       // 31+
                list += Manifest.permission.BLUETOOTH_ADVERTISE
                list += Manifest.permission.BLUETOOTH_CONNECT
                list += Manifest.permission.BLUETOOTH_SCAN
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) { // 33+
                list += Manifest.permission.NEARBY_WIFI_DEVICES
            } else {
                list += Manifest.permission.ACCESS_FINE_LOCATION
            }
            return list.toTypedArray()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val permissionLauncher = registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { /* Nearby simply won't connect if denied; grant all for the demo. */ }

        permissionLauncher.launch(requiredPermissions)

        setContent {
            RelayTheme {
                RelayRoot()
            }
        }
    }
}
