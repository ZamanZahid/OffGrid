import Foundation

enum ServerConfig {
    /// Simulator reaches the Mac host via loopback; physical devices use LAN IP.
    static var baseURL: URL {
        #if targetEnvironment(simulator)
        return URL(string: "http://127.0.0.1:8080")!
        #else
        return URL(string: "http://192.168.0.164:8080")!
        #endif
    }

    static var baseURLString: String { baseURL.absoluteString }
}
