import SwiftUI

struct ContentView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        if let role = app.role {
            switch role {
            case .sender:
                TabView {
                    SenderView()
                        .tabItem { Label("Send", systemImage: "paperplane") }
                    RelayView()
                        .tabItem { Label("Relay", systemImage: "antenna.radiowaves.left.and.right") }
                    RecipientView()
                        .tabItem { Label("Inbox", systemImage: "tray") }
                    SkygazeView()
                        .tabItem { Label("Skygaze", systemImage: "star") }
                }
                .navigationTitle("Offgrid")
                .navigationBarTitleDisplayMode(.inline)
            case .relay:
                TabView {
                    RelayView()
                        .tabItem { Label("Relay", systemImage: "antenna.radiowaves.left.and.right") }
                    SkygazeView()
                        .tabItem { Label("Skygaze", systemImage: "star") }
                }
                .navigationTitle("Offgrid")
                .navigationBarTitleDisplayMode(.inline)
            case .recipient:
                TabView {
                    RecipientView()
                        .tabItem { Label("Inbox", systemImage: "tray") }
                    SkygazeView()
                        .tabItem { Label("Skygaze", systemImage: "star") }
                }
                .navigationTitle("Offgrid")
                .navigationBarTitleDisplayMode(.inline)
            }
        } else {
            RoleSelectionView()
        }
    }
}
