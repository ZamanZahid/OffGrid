import Foundation
import MultipeerConnectivity

/// Thin wrapper over MultipeerConnectivity. Every device both advertises and
/// browses for the same service and auto-connects. The rest of the app just
/// calls `send(_:)` and reacts to `onReceive` / `onPeersChanged`.
///
/// Transport: MultipeerConnectivity uses Bluetooth and/or peer-to-peer Wi-Fi.
/// With the Sender in Airplane Mode + Bluetooth ON, it runs over Bluetooth —
/// which is exactly the "no internet, hand it to a nearby phone" story.
final class MultipeerSession: NSObject, ObservableObject {

    // ≤15 chars, lowercase letters / numbers / hyphens. Must match the Bonjour
    // service names in Info.plist (_relay-demo._tcp / _relay-demo._udp).
    private let serviceType = "relay-demo"

    private let myPeerID: MCPeerID
    private let session: MCSession
    private let advertiser: MCNearbyServiceAdvertiser
    private let browser: MCNearbyServiceBrowser

    @Published private(set) var connectedPeers: [MCPeerID] = []

    /// Called on the main thread when a peer sends us data.
    var onReceive: ((Data, MCPeerID) -> Void)?
    /// Called on the main thread whenever the connected-peer set changes.
    var onPeersChanged: (([MCPeerID]) -> Void)?

    init(displayName: String) {
        myPeerID = MCPeerID(displayName: displayName)
        session = MCSession(peer: myPeerID,
                            securityIdentity: nil,
                            encryptionPreference: .required)
        advertiser = MCNearbyServiceAdvertiser(peer: myPeerID,
                                               discoveryInfo: nil,
                                               serviceType: serviceType)
        browser = MCNearbyServiceBrowser(peer: myPeerID, serviceType: serviceType)
        super.init()
        session.delegate = self
        advertiser.delegate = self
        browser.delegate = self
    }

    func start() {
        advertiser.startAdvertisingPeer()
        browser.startBrowsingForPeers()
    }

    func stop() {
        advertiser.stopAdvertisingPeer()
        browser.stopBrowsingForPeers()
        session.disconnect()
    }

    /// Send to every connected peer. Returns false if nobody is connected.
    @discardableResult
    func send(_ data: Data) -> Bool {
        guard !session.connectedPeers.isEmpty else { return false }
        do {
            try session.send(data, toPeers: session.connectedPeers, with: .reliable)
            return true
        } catch {
            print("MPC send error:", error)
            return false
        }
    }
}

// MARK: - Session
extension MultipeerSession: MCSessionDelegate {
    func session(_ session: MCSession, peer peerID: MCPeerID, didChange state: MCSessionState) {
        DispatchQueue.main.async {
            self.connectedPeers = session.connectedPeers
            self.onPeersChanged?(session.connectedPeers)
        }
    }
    func session(_ session: MCSession, didReceive data: Data, fromPeer peerID: MCPeerID) {
        DispatchQueue.main.async {
            self.onReceive?(data, peerID)
        }
    }
    func session(_ s: MCSession, didReceive stream: InputStream, withName n: String, fromPeer p: MCPeerID) {}
    func session(_ s: MCSession, didStartReceivingResourceWithName n: String, fromPeer p: MCPeerID, with progress: Progress) {}
    func session(_ s: MCSession, didFinishReceivingResourceWithName n: String, fromPeer p: MCPeerID, at localURL: URL?, withError error: Error?) {}
}

// MARK: - Advertiser (auto-accept invitations for the demo)
extension MultipeerSession: MCNearbyServiceAdvertiserDelegate {
    func advertiser(_ advertiser: MCNearbyServiceAdvertiser,
                    didReceiveInvitationFromPeer peerID: MCPeerID,
                    withContext context: Data?,
                    invitationHandler: @escaping (Bool, MCSession?) -> Void) {
        invitationHandler(true, session)
    }
}

// MARK: - Browser (auto-invite found peers)
extension MultipeerSession: MCNearbyServiceBrowserDelegate {
    func browser(_ browser: MCNearbyServiceBrowser,
                 foundPeer peerID: MCPeerID,
                 withDiscoveryInfo info: [String : String]?) {
        // Both sides find each other; only the lexicographically-smaller name
        // sends the invite so we don't race into a double connection.
        if myPeerID.displayName < peerID.displayName {
            browser.invitePeer(peerID, to: session, withContext: nil, timeout: 15)
        }
    }
    func browser(_ browser: MCNearbyServiceBrowser, lostPeer peerID: MCPeerID) {}
}
