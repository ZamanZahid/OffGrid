# Relay (Android) — *Find My, but for messages*

Send a message with **zero signal**. Your phone hands the (encrypted) message to a
nearby phone over **Bluetooth / Wi-Fi Direct**, and *that* phone's internet
delivers it. The relaying stranger — and the server — only ever see ciphertext.

```
[A: offline]  --Nearby Connections (BT/Wi-Fi Direct)-->  [B: relay, online]  --HTTP-->  [server]  --poll-->  [C: recipient]
   encrypts                                                 can't decrypt                 stores            decrypts
```

This is the Android port of the iOS concept. **Everything builds on Windows** —
no Mac needed.

---

## Why Android here
- Android dev is fully supported on **Windows** (Android Studio). No Mac, no cloud Mac.
- The Bluetooth hop uses Google's **Nearby Connections API** — the Android analog
  of iOS MultipeerConnectivity; it auto-picks Bluetooth and/or Wi-Fi Direct, so it
  works with no internet.
- Same E2E crypto story (X25519 → HKDF → AES-256-GCM via BouncyCastle).

## What's here
```
android/
├── build.gradle.kts · settings.gradle.kts · gradle.properties
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── AndroidManifest.xml          # all the Bluetooth/Wi-Fi permissions
│       ├── res/values/                  # strings, theme
│       └── java/com/relay/app/
│           ├── MainActivity.kt          # Compose host + runtime permissions
│           ├── AppViewModel.kt          # state + role logic  ← set serverUrl here
│           ├── model/Models.kt          # Envelope + Ack
│           ├── crypto/Crypto.kt         # X25519 + HKDF + AES-GCM + demo keys
│           ├── net/NearbyTransport.kt   # Bluetooth/Wi-Fi peer transport
│           ├── net/Backend.kt           # MessageBackend + RestBackend (polling)
│           └── ui/Theme.kt · ui/Screens.kt
└── (server is shared) ../server/server.py
```

## Requirements
- **Android Studio** (Ladybug / 2024.2+), JDK 17 (bundled).
- **Two physical Android phones** for the Bluetooth hop (emulators have no real
  Bluetooth). The Recipient can be a 3rd phone *or* the relay phone itself.
- Phones must have **Google Play Services** (Nearby Connections needs it).
- The Sender + Relay must be **physically near each other** (same room).

## Setup (≈10 min)
1. **Open** the `android/` folder in Android Studio → let it sync (it downloads
   Gradle + SDKs automatically). If it asks to create the Gradle wrapper, accept.
2. **Run the server** on a laptop on the same Wi-Fi as the relay + recipient:
   ```
   python3 ../server/server.py
   ```
   Grab the laptop's LAN IP (e.g. `192.168.1.50`).
3. **Point the app at it.** In `AppViewModel.kt`, set
   `serverUrl = "http://<laptop-LAN-IP>:8080"`.
4. **Build & run** on each phone (USB debugging on, or wireless debugging).
   Grant the Bluetooth/Nearby permissions when prompted, then tap a role.

## The demo (≈20 sec on stage)
1. **Sender phone → Airplane Mode ON, then Bluetooth ON.** Provably offline — no
   Wi-Fi, no cellular — yet Bluetooth works. Show the audience the quick-settings.
2. **Relay + Recipient** stay on normal Wi-Fi.
3. On the Sender, wait for **"Relay found nearby"**, type a message, hit **Send**.
4. The timeline fills in — *Searching → Relay found → Handed to relay over
   Bluetooth → Delivered ✓* — on a phone with no internet.
5. **Recipient** lights up with the decrypted message.
6. **Punchline:** show the **Relay** screen — it logged the message as an
   unreadable ciphertext blob. *"This stranger carried your message and never
   could read it."*

## Gotchas (Nearby Connections is finicky — read this)
- **Turn ON Location (GPS toggle)** on the phones. Nearby/BLE discovery silently
  fails on many Android versions if system Location is off, even with permissions.
- **Bluetooth ON** on all devices; **Wi-Fi ON** on relay + recipient.
- Grant **all** requested permissions. A denied Bluetooth/Nearby permission =
  no discovery, no error.
- Keep Sender + Relay within a few meters.
- **Test on the actual phones beforehand** and **record a backup video** — crowded
  rooms are full of Bluetooth interference and live BLE demos flake.

## How the privacy works (judge bait)
`crypto/Crypto.kt`: the sender makes a throwaway X25519 keypair, does ECDH against
the recipient's public key, derives a key with HKDF-SHA256, and seals the text with
AES-256-GCM. Only the recipient's private key reproduces that shared secret. The
relay and server move opaque bytes — even we can't read messages.

## Honest "future work" slide
- Multi-hop mesh (relay → relay → … → internet)
- Store-and-forward when no relay is in range yet (delay-tolerant networking)
- Real key exchange (QR / directory) instead of the hardcoded demo key
- Background relaying via a foreground service + persistent Nearby advertising
- Spam/abuse limits and relayer privacy

## Swapping the backend
`RestBackend` is one implementation of `MessageBackend`. Drop in a Firebase/Ktor
WebSocket version (realtime instead of polling, delivery over cellular so the
recipient can be anywhere) without touching the UI or crypto — just change which
backend `AppViewModel.choose()` constructs.
