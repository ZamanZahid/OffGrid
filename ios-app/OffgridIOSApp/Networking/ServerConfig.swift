import Foundation

extension Array where Element == URL {
    fileprivate func unique() -> [URL] {
        var seen = Set<String>()
        return filter {
            let key = $0.absoluteString
            guard !seen.contains(key) else { return false }
            seen.insert(key)
            return true
        }
    }
}

enum ServerConfig {
    private static let overrideKey = "OffgridServerURL"

    /// Simulator reaches the Mac host via loopback; physical devices need the laptop's
    /// LAN IP. The app first checks a user override, then tries a few common private-net
    /// addresses that are frequently used for local demo setups.
    static var baseURL: URL {
        if let override = UserDefaults.standard.string(forKey: overrideKey),
           let url = URL(string: override) {
            return url
        }

        #if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8080")!
        #else
        return URL(string: "http://192.168.0.164:8080")!
        #endif
    }

    static var fallbackURLs: [URL] {
        let localIPs = [
            "192.168.0.164",
            "192.168.1.50",
            "192.168.1.1",
            "192.168.0.1",
            "10.0.0.1",
            "10.0.1.1",
            "172.16.0.1",
            "172.20.0.1",
        ]

        return localIPs
            .map { "http://\($0):8080" }
            .compactMap { URL(string: $0) }
            .unique() // preserve order while avoiding duplicates
    }

    static var baseURLString: String { baseURL.absoluteString }
}
