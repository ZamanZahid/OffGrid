import SwiftUI
import UIKit

@main
struct OffgridIOSAppApp: App {
    @StateObject private var app = AppModel()
    @StateObject private var connectivity = ConnectivityMonitor()

    init() {
        let nav = UINavigationBarAppearance()
        nav.configureWithTransparentBackground()
        UINavigationBar.appearance().standardAppearance = nav
        UINavigationBar.appearance().scrollEdgeAppearance = nav

        let tab = UITabBarAppearance()
        tab.configureWithDefaultBackground()
        tab.backgroundColor = UIColor(white: 0, alpha: 0.92)
        UITabBar.appearance().standardAppearance = tab
        UITabBar.appearance().scrollEdgeAppearance = tab

        UIScrollView.appearance().backgroundColor = .clear
        UITableView.appearance().backgroundColor = .clear
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .environmentObject(app)
                .environmentObject(connectivity)
                .preferredColorScheme(.dark)
                .tint(AppTheme.accent)
        }
    }
}
