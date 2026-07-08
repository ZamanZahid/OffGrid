import SwiftUI

@main
struct RelayApp: App {
    @StateObject private var app = AppModel()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ContentView()
            }
            .environmentObject(app)
        }
    }
}
