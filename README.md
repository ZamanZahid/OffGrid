<div align="center">

# Offgrid, Aerogaze + Relay

Two offline systems for when the grid goes down: find your location from the stars, and send a message with zero signal.

![AeroGaze Screenshot](./orion_detect.png)


**AeroGaze:**
- Handle display/EXIF rotation for real-photo capture paths
- Foreground-service gravity sampler for better timing accuracy
- Expand star catalog coverage
- Enhanced mobile UI + offline map/pin integration

**Relay:**
- Multi-hop mesh relaying (relay → relay → … → internet)
- Store-and-forward when no relay is in range yet (delay-tolerant networking)
- Real key exchange (QR code / directory) instead of a hardcoded demo key
- Background relaying via a foreground service with persistent Nearby advertising
- Spam/abuse limits and relayer privacy protections
- Swappable realtime backend (e.g. Firebase/Ktor WebSocket) in place of HTTP polling — `RestBackend` already implements a generic `MessageBackend` interface, so this is a drop-in change
