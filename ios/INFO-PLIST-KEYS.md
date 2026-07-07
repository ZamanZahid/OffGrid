# Info.plist keys (required — the app won't connect without these)

In Xcode: select the target → **Info** tab → add these rows. Or paste the XML
below into your Info.plist source.

| Key | Type | Value |
|---|---|---|
| `NSLocalNetworkUsageDescription` | String | `Relay hands your message to a nearby phone when you're offline.` |
| `NSBluetoothAlwaysUsageDescription` | String | `Relay uses Bluetooth to reach nearby phones with no internet.` |
| `NSBonjourServices` | Array | two items below |
| → item 0 | String | `_relay-demo._tcp` |
| → item 1 | String | `_relay-demo._udp` |
| `NSAppTransportSecurity` → `NSAllowsArbitraryLoads` | Bool | `YES` *(demo only — lets the app talk to the plain-HTTP server)* |

> The Bonjour service names **must** match `serviceType = "relay-demo"` in
> `MultipeerSession.swift`.

## XML (paste inside the top-level `<dict>`)

```xml
<key>NSLocalNetworkUsageDescription</key>
<string>Relay hands your message to a nearby phone when you're offline.</string>

<key>NSBluetoothAlwaysUsageDescription</key>
<string>Relay uses Bluetooth to reach nearby phones with no internet.</string>

<key>NSBonjourServices</key>
<array>
    <string>_relay-demo._tcp</string>
    <string>_relay-demo._udp</string>
</array>

<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```
