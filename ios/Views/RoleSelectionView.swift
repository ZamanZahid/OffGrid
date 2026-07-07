import SwiftUI

struct RoleSelectionView: View {
    @EnvironmentObject var app: AppModel

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 56))
                .foregroundStyle(.tint)
            Text("Relay")
                .font(.largeTitle.bold())
            Text("Find My, but for messages.")
                .foregroundStyle(.secondary)
            Spacer()

            Text("Pick this device's role")
                .font(.footnote)
                .foregroundStyle(.secondary)

            ForEach(Role.allCases) { role in
                Button {
                    app.choose(role: role)
                } label: {
                    Label(role.rawValue, systemImage: role.icon)
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
        }
        .padding(32)
    }
}
