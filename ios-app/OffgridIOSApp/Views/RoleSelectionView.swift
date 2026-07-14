import SwiftUI

struct RoleSelectionView: View {
    @EnvironmentObject var app: AppModel
    @State private var showAbout = false

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            ScrollView {
                VStack(spacing: 20) {
                    VStack(spacing: 8) {
                        Text("Offgrid")
                            .font(.system(size: 48, weight: .bold, design: .rounded))
                            .foregroundStyle(.white)

                        Text("Find my, for when your lost")
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)

                    Rectangle()
                        .fill(AppTheme.border)
                        .frame(height: 1)
                        .padding(.vertical, 8)

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Pick this device's role")
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(AppTheme.muted)
                            .textCase(.uppercase)
                            .frame(maxWidth: .infinity, alignment: .center)

                        ForEach(Role.allCases) { role in
                            OffgridPrimaryButton(
                                title: role.title,
                                subtitle: role.subtitle,
                                icon: role.icon
                            ) {
                                app.choose(role: role)
                            }
                        }
                    }
                    .frame(maxWidth: 480)
                    .frame(maxWidth: .infinity)

                    HStack(spacing: 16) {
                        Rectangle()
                            .fill(AppTheme.border)
                            .frame(height: 1)
                        Text("or explore")
                            .font(.caption.weight(.medium))
                            .foregroundStyle(AppTheme.muted)
                            .fixedSize()
                        Rectangle()
                            .fill(AppTheme.border)
                            .frame(height: 1)
                    }
                    .padding(.vertical, 4)
                    .frame(maxWidth: 480)
                    .frame(maxWidth: .infinity)

                    OffgridPrimaryButton(
                        title: "SkyGaze",
                        subtitle: "Offline star positioning\nfrom a night sky photo",
                        icon: "sparkles",
                        tint: AppTheme.accentSecondary,
                        centerTitle: true,
                        centerSubtitle: true,
                        larger: true
                    ) {
                        app.enterSkygaze()
                    }
                    .frame(maxWidth: 480)
                    .frame(maxWidth: .infinity)
                }
                .padding(.horizontal, 24)
                .padding(.top, 72)
                .padding(.bottom, 20)
            }
            .scrollContentBackground(.hidden)
            .background(Color.clear)

            Button {
                showAbout = true
            } label: {
                Text("?")
                    .font(.subheadline.weight(.bold))
                    .foregroundStyle(AppTheme.muted)
                    .frame(width: 36, height: 36)
                    .background(AppTheme.card)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(AppTheme.border, lineWidth: 1))
            }
            .buttonStyle(.plain)
            .padding(.trailing, 20)
            .padding(.bottom, 16)
        }
        .sheet(isPresented: $showAbout) {
            AboutOffgridSheet()
        }
    }
}

private struct AboutOffgridSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 20) {
                    Text("About Offgrid")
                        .font(.title2.bold())
                        .foregroundStyle(.white)

                    VStack(alignment: .center, spacing: 16) {
                        Text("Whether you're stuck in the middle of a forest, drifting out at sea, or just stuck somewhere with no signal — Offgrid keeps you connected. Relay sends encrypted messages phone-to-phone over Bluetooth until one reaches the internet, and nobody in between can read what's inside")
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                            .multilineTextAlignment(.center)

                        Text("Pick a role on the home screen: Sender to send a message, Relay to pass one along, or Recipient to read your inbox. Lost without GPS? AeroGaze finds your location from a single photo of the night sky.")
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.muted)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity, alignment: .center)

                    Rectangle()
                        .fill(AppTheme.border)
                        .frame(height: 1)

                    Button {
                        dismiss()
                    } label: {
                        Text("Done")
                            .font(.headline)
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(AppTheme.accent.opacity(0.22))
                            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .overlay(
                                RoundedRectangle(cornerRadius: 14, style: .continuous)
                                    .stroke(AppTheme.accent.opacity(0.45), lineWidth: 1)
                            )
                    }
                    .buttonStyle(.plain)
                }
                .padding(24)
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .presentationBackground(Color.black)
    }
}
