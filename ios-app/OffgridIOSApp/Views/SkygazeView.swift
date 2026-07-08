import SwiftUI

struct SkygazeView: View {
    @State private var isDemoRunning = false
    @State private var lastResult = "Tap to run the demo solver."

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Label("AeroGaze", systemImage: "sparkles")
                    .font(.title2.bold())

                Text("This screen mirrors the Android Skygaze flow: capture, gravity, and star-solving are wired as an iOS-native entrypoint for the same offline positioning engine.")
                    .foregroundStyle(.secondary)

                Button {
                    isDemoRunning = true
                    lastResult = "Preparing demo solve…"
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                        isDemoRunning = false
                        lastResult = "Demo ready. The native iOS app can now host the solver UI and camera pipeline."
                    }
                } label: {
                    Label("Run demo solve", systemImage: "play.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                if isDemoRunning {
                    ProgressView("Preparing demo solve…")
                        .padding(.vertical)
                }

                RoundedRectangle(cornerRadius: 16)
                    .fill(.quaternary)
                    .frame(height: 180)
                    .overlay(
                        VStack(spacing: 8) {
                            Image(systemName: "star.fill")
                                .font(.system(size: 34))
                            Text("Offline star positioning")
                                .font(.headline)
                            Text("Camera + IMU + sky matching")
                                .foregroundStyle(.secondary)
                        }
                    )

                Text(lastResult)
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
            .padding()
        }
        .navigationTitle("Skygaze")
        .navigationBarTitleDisplayMode(.inline)
    }
}
