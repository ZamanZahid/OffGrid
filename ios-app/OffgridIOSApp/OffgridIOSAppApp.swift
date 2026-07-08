import SwiftUI

@main
struct OffgridIOSAppApp: App {
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
