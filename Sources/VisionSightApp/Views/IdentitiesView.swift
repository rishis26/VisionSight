import SwiftUI
import VisionSightLib

struct IdentitiesView: View {
    @ObservedObject var appState: AppState
    @State private var newName: String = ""
    @State private var isCapturing: Bool = false
    @State private var statusMessage: String?
    @State private var isError: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Registered Identities")
                .font(.system(size: 28, weight: .bold))

            // Registration Form
            VStack(alignment: .leading, spacing: 12) {
                Text("ENROLL NEW FACE")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)

                HStack {
                    TextField("Enter full name...", text: $newName)
                        .textFieldStyle(.roundedBorder)

                    Button {
                        enrollFace()
                    } label: {
                        if isCapturing {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Label("Register Face", systemImage: "camera.fill")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newName.trimmingCharacters(in: .whitespaces).isEmpty || isCapturing)
                }

                if let msg = statusMessage {
                    Text(msg)
                        .font(.caption)
                        .foregroundStyle(isError ? .red : .green)
                }
            }
            .padding(20)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // List of Identities
            VStack(alignment: .leading, spacing: 12) {
                Text("ENROLLED PROFILES (\(appState.identities.count))")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)

                if appState.identities.isEmpty {
                    ContentUnavailableView(
                        "No Identities Registered",
                        systemImage: "person.crop.circle.badge.plus",
                        description: Text("Enroll your face above to enable auto-unlock.")
                    )
                    .padding()
                } else {
                    List {
                        ForEach(appState.identities) { id in
                            HStack {
                                Image(systemName: "faceid")
                                    .font(.title2)
                                    .foregroundStyle(.blue)

                                VStack(alignment: .leading, spacing: 2) {
                                    Text(id.name)
                                        .font(.headline)
                                    Text("Enrolled: \(id.registeredAt.formatted(date: .abbreviated, time: .shortened))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }

                                Spacer()

                                Button(role: .destructive) {
                                    appState.removeIdentity(named: id.name)
                                } label: {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.borderless)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                    .listStyle(.inset)
                }
            }
            .padding(20)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            Spacer()
        }
        .padding(30)
    }

    private func enrollFace() {
        let name = newName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }

        isCapturing = true
        statusMessage = "Accessing camera..."
        isError = false

        Task {
            let camera = CameraController()
            guard let pixelBuffer = camera.capturePhoto() else {
                await MainActor.run {
                    statusMessage = "Failed to capture photo from webcam."
                    isError = true
                    isCapturing = false
                }
                return
            }
            camera.stop()

            let engine = FaceEngine()
            do {
                let faces = try engine.detectFaces(in: pixelBuffer)
                guard !faces.isEmpty else {
                    await MainActor.run {
                        statusMessage = "No face detected in frame. Ensure adequate lighting."
                        isError = true
                        isCapturing = false
                    }
                    return
                }

                guard faces.count == 1 else {
                    await MainActor.run {
                        statusMessage = "Multiple faces detected (\(faces.count)). Frame only one person."
                        isError = true
                        isCapturing = false
                    }
                    return
                }

                guard let fp = try engine.generateFeaturePrint(from: pixelBuffer, face: faces[0]) else {
                    await MainActor.run {
                        statusMessage = "Could not generate biometric face embedding."
                        isError = true
                        isCapturing = false
                    }
                    return
                }

                let id = try Identity(name: name, featurePrint: fp)
                try IdentityStore.register(id)

                await MainActor.run {
                    appState.refreshIdentities()
                    newName = ""
                    statusMessage = "Profile for '\(name)' successfully registered!"
                    isError = false
                    isCapturing = false
                }
            } catch {
                await MainActor.run {
                    statusMessage = "Enrollment error: \(error.localizedDescription)"
                    isError = true
                    isCapturing = false
                }
            }
        }
    }
}
