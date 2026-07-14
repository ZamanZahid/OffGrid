import SwiftUI
import UIKit

/// Clears the opaque background UIKit adds behind TabView pages.
private struct TabViewBackgroundClearer: UIViewRepresentable {
    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.isUserInteractionEnabled = false
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            var responder: UIResponder? = uiView
            while let next = responder?.next {
                if let tabBar = next as? UITabBarController {
                    tabBar.view.backgroundColor = .clear
                    tabBar.view.isOpaque = false
                    tabBar.viewControllers?.forEach { child in
                        child.view.backgroundColor = .clear
                        child.view.isOpaque = false
                    }
                    break
                }
                if let vc = next as? UIViewController {
                    vc.view.backgroundColor = .clear
                    vc.view.isOpaque = false
                }
                responder = next
            }
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        ZStack {
            ConstellationBackground()
                .ignoresSafeArea()

            Group {
                if let role = app.role {
                    mainTabs(for: role)
                } else {
                    RoleSelectionView()
                }
            }
        }
        .background(Color.black)
    }

    @ViewBuilder
    private func mainTabs(for role: Role) -> some View {
        TabView(selection: $app.selectedTab) {
            ForEach(role.visibleTabs, id: \.self) { tab in
                tabContent(for: tab)
                    .tag(tab)
                    .tabItem {
                        Label(tab.title, systemImage: tab.icon)
                    }
            }
        }
        .background(Color.clear)
        .background(TabViewBackgroundClearer())
        .toolbarBackground(Color.black.opacity(0.92), for: .tabBar)
        .toolbarBackground(.visible, for: .tabBar)
        .onAppear {
            if !role.visibleTabs.contains(app.selectedTab) {
                app.selectedTab = role.defaultTab
            }
        }
    }

    @ViewBuilder
    private func tabContent(for tab: AppTab) -> some View {
        ZStack {
            ConstellationBackground()
                .ignoresSafeArea()

            switch tab {
            case .send:
                SenderView()
            case .relay:
                RelayView()
            case .inbox:
                RecipientView()
            case .skygaze:
                SkygazeView()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.clear)
    }
}
