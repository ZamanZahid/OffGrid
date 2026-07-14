import SwiftUI

struct SkygazeView: View {
    @State private var isDemoRunning = false
    @State private var lastResult = "Tap to run the demo solver."
    @State private var errorMessage: String?
    @State private var lastMetrics: DemoSolveMetrics?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Label("AeroGaze", systemImage: "sparkles")
                    .font(.title2.bold())

                Text("This screen mirrors the Android Skygaze flow: capture, gravity, and star-solving are wired as an iOS-native entrypoint for the same offline positioning engine.")
                    .foregroundStyle(.secondary)

                Button {
                    Task {
                        await runDemoSolve()
                    }
                } label: {
                    Label("Run demo solve", systemImage: "play.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)

                if isDemoRunning {
                    ProgressView("Running demo solve…")
                        .padding(.vertical)
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.callout)
                        .foregroundStyle(.red)
                }

                if let metrics = lastMetrics {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Recovered position")
                            .font(.headline)
                        Text("lat \(String(format: "%.4f", metrics.recoveredLat ?? 0.0)), lon \(String(format: "%.4f", metrics.recoveredLon ?? 0.0))")
                        Text("Error: \(String(format: "%.2f", metrics.errorKm ?? 0.0)) km")
                        Text("Stars: \(Int(metrics.starsDetected ?? 0)) • Inliers: \(Int(metrics.inlierMatches ?? 0))")
                        Text("Residual: \(String(format: "%.1f", metrics.residualArcsec ?? 0.0)) arcsec")
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
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

    private func runDemoSolve() async {
        isDemoRunning = true
        errorMessage = nil
        lastResult = "Preparing demo solve…"

        guard let url = URL(string: "http://192.168.0.164:8080/demo-solve") else {
            isDemoRunning = false
            lastResult = "Invalid server URL."
            errorMessage = "Set the server IP to your laptop LAN address in SkygazeView.swift."
            return
        }

        do {
            var req = URLRequest(url: url)
            req.httpMethod = "POST"
            let (data, response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            let decoded = try JSONDecoder().decode(DemoSolveResponse.self, from: data)
            await MainActor.run {
                isDemoRunning = false
                if decoded.ok {
                    lastResult = "Demo solve completed."
                    lastMetrics = DemoSolveMetrics(recoveredLat: decoded.recoveredLat,
                                                   recoveredLon: decoded.recoveredLon,
                                                   errorKm: decoded.errorKm,
                                                   starsDetected: decoded.starsDetected,
                                                   inlierMatches: decoded.inlierMatches,
                                                   residualArcsec: decoded.residualArcsec)
                } else {
                    lastResult = "Demo solve failed."
                    errorMessage = decoded.output?.prefix(400).description ?? "No error details returned."
                }
            }
        } catch {
            await MainActor.run {
                isDemoRunning = false
                lastResult = "Demo solve failed."
                errorMessage = error.localizedDescription
            }
        }
    }
}

struct DemoSolveResponse: Decodable {
    let ok: Bool
    let recoveredLat: Double?
    let recoveredLon: Double?
    let errorKm: Double?
    let starsDetected: Double?
    let inlierMatches: Double?
    let residualArcsec: Double?
    let output: String?
}

struct DemoSolveMetrics {
    let recoveredLat: Double?
    let recoveredLon: Double?
    let errorKm: Double?
    let starsDetected: Double?
    let inlierMatches: Double?
    let residualArcsec: Double?
}
