import SwiftUI

struct SkygazeView: View {
    @State private var isDemoRunning = false
    @State private var lastResult = "Take a night-sky photo or choose one from your library."
    @State private var errorMessage: String?
    @State private var lastMetrics: DemoSolveMetrics?

    @State private var showImagePicker = false
    @State private var imageSource: UIImagePickerController.SourceType = .photoLibrary
    @State private var selectedImage: UIImage?
    @State private var selectedImageData: Data?
    @State private var showSolveOptions = false
    @State private var altDegrees = "90"
    @State private var utcString = ISO8601DateFormatter().string(from: Date())

    private var serverBaseURL: String { ServerConfig.baseURLString }

    var body: some View {
        OffgridPageContainer(contentTopPadding: 36) {
                OffgridSectionHeader(
                    title: "AeroGaze",
                    subtitle: "Take a night-sky photo or pick one from your library, then solve it through the AeroGaze backend.",
                    topPadding: 8
                )

                ConnectivityBadge()
                    .frame(maxWidth: .infinity)

                HStack(spacing: 12) {
                    Button(action: { imageSource = .camera; showImagePicker = true }) {
                        Label("Take Photo", systemImage: "camera.fill")
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.accentSecondary)
                    .disabled(!UIImagePickerController.isSourceTypeAvailable(.camera))

                    Button(action: { imageSource = .photoLibrary; showImagePicker = true }) {
                        Label("Pick Photo", systemImage: "photo.fill")
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.accent)
                }

                if let image = selectedImage {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 240)
                        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 18, style: .continuous)
                                .stroke(AppTheme.border, lineWidth: 1)
                        )
                }

                if selectedImageData != nil {
                    Button(action: { showSolveOptions = true }) {
                        Label("Solve selected photo", systemImage: "play.circle.fill")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(AppTheme.success)
                }

                if isDemoRunning {
                    HStack(spacing: 12) {
                        ProgressView()
                            .tint(AppTheme.accent)
                        Text("Solving photo…")
                            .foregroundStyle(AppTheme.muted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .offgridCard(padding: 14)
                }

                if let errorMessage {
                    Text(errorMessage)
                        .font(.callout)
                        .foregroundStyle(AppTheme.danger)
                        .offgridCard(padding: 14)
                }

                if let metrics = lastMetrics {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recovered position")
                            .font(.headline)
                            .foregroundStyle(.white)
                        metricRow("Latitude", String(format: "%.4f", metrics.recoveredLat ?? 0.0))
                        metricRow("Longitude", String(format: "%.4f", metrics.recoveredLon ?? 0.0))
                        metricRow("Error", "\(String(format: "%.2f", metrics.errorKm ?? 0.0)) km")
                        metricRow("Stars", "\(Int(metrics.starsDetected ?? 0)) detected")
                        metricRow("Inliers", "\(Int(metrics.inlierMatches ?? 0)) matches")
                        metricRow("Residual", "\(String(format: "%.1f", metrics.residualArcsec ?? 0.0)) arcsec")
                    }
                    .offgridCard()
                }

                VStack(spacing: 10) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 34))
                        .foregroundStyle(AppTheme.accentSecondary)
                    Text("Offline star positioning")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Text("Camera + backend solve")
                        .foregroundStyle(AppTheme.muted)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 28)
                .offgridCard()

                Text(lastResult)
                    .font(.callout)
                    .foregroundStyle(AppTheme.muted)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
        }
        .sheet(isPresented: $showImagePicker) {
            ImagePicker(sourceType: imageSource, selectedImage: $selectedImage, imageData: $selectedImageData, isPresented: $showImagePicker)
        }
        .sheet(isPresented: $showSolveOptions) {
            VStack(spacing: 16) {
                Text("Photo solve options")
                    .font(.headline)
                    .foregroundStyle(.white)
                    .padding(.top)

                TextField("Camera angle above horizon (90 = straight up)", text: $altDegrees)
                    .padding(12)
                    .background(AppTheme.card)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .keyboardType(.decimalPad)

                TextField("UTC timestamp", text: $utcString)
                    .padding(12)
                    .background(AppTheme.card)
                    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                    .autocorrectionDisabled(true)
                    .textInputAutocapitalization(.never)

                HStack {
                    Button("Cancel") { showSolveOptions = false }
                        .foregroundStyle(AppTheme.muted)
                    Spacer()
                    Button("Solve") {
                        showSolveOptions = false
                        Task {
                            await solveSelectedPhoto()
                        }
                    }
                    .fontWeight(.semibold)
                    .foregroundStyle(AppTheme.accent)
                    .disabled(selectedImageData == nil)
                }
                .padding([.horizontal, .bottom])
            }
            .padding()
            .presentationBackground(AppTheme.backgroundBottom)
            .preferredColorScheme(.dark)
        }
    }

    private func metricRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(AppTheme.muted)
            Spacer()
            Text(value)
                .foregroundStyle(.white)
                .fontWeight(.medium)
        }
        .font(.subheadline)
    }

    private func solveSelectedPhoto() async {
        guard let photoData = selectedImageData else {
            errorMessage = "No photo selected."
            return
        }

        isDemoRunning = true
        errorMessage = nil
        lastResult = "Sending photo to solver…"
        lastMetrics = nil

        let urlString = "\(serverBaseURL)/solve-photo"
        guard let url = URL(string: urlString) else {
            isDemoRunning = false
            lastResult = "Invalid server URL."
            errorMessage = "Set serverBaseURL to your laptop IP in SkygazeView.swift."
            return
        }

        let timestampUTC = utcString
        let alt = Double(altDegrees) ?? 90.0
        let roll = 0.0
        let fov = 60.0
        let payload: [String: Any] = [
            "image_b64": photoData.base64EncodedString(),
            "timestamp_utc": timestampUTC,
            "alt_deg": alt,
            "roll_deg": roll,
            "fov_deg": fov,
        ]

        do {
            let jsonData = try JSONSerialization.data(withJSONObject: payload, options: [])
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = jsonData

            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }

            let decoded = try JSONDecoder().decode(DemoSolveResponse.self, from: data)
            await MainActor.run {
                isDemoRunning = false
                if decoded.ok {
                    lastResult = "Photo solve completed."
                    lastMetrics = DemoSolveMetrics(
                        recoveredLat: decoded.recoveredLat,
                        recoveredLon: decoded.recoveredLon,
                        errorKm: decoded.errorKm,
                        starsDetected: decoded.starsDetected,
                        inlierMatches: decoded.inlierMatches,
                        residualArcsec: decoded.residualArcsec
                    )
                } else {
                    lastResult = "Photo solve failed."
                    errorMessage = decoded.error ?? decoded.output?.prefix(400).description ?? "Solver returned no details."
                }
            }
        } catch {
            await MainActor.run {
                isDemoRunning = false
                lastResult = "Photo solve failed."
                errorMessage = error.localizedDescription
            }
        }
    }
}

struct ImagePicker: UIViewControllerRepresentable {
    let sourceType: UIImagePickerController.SourceType
    @Binding var selectedImage: UIImage?
    @Binding var imageData: Data?
    @Binding var isPresented: Bool

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = sourceType
        picker.delegate = context.coordinator
        picker.allowsEditing = false
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: ImagePicker

        init(_ parent: ImagePicker) {
            self.parent = parent
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.isPresented = false
        }

        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey : Any]) {
            if let uiImage = info[.originalImage] as? UIImage {
                parent.selectedImage = uiImage
                parent.imageData = uiImage.jpegData(compressionQuality: 0.85)
            }
            parent.isPresented = false
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
    let error: String?

    enum CodingKeys: String, CodingKey {
        case ok
        case recoveredLat = "recovered_lat"
        case recoveredLon = "recovered_lon"
        case errorKm = "error_km"
        case starsDetected = "stars_detected"
        case inlierMatches = "inlier_matches"
        case residualArcsec = "residual_arcsec"
        case output
        case error
    }
}

struct DemoSolveMetrics {
    let recoveredLat: Double?
    let recoveredLon: Double?
    let errorKm: Double?
    let starsDetected: Double?
    let inlierMatches: Double?
    let residualArcsec: Double?
}
