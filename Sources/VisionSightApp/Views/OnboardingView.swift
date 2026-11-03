import SwiftUI
import VisionSightLib

struct OnboardingView: View {
    @ObservedObject var appState: AppState
    @State private var step: Int = 0

    @State private var passwordInput: String = ""
    @State private var identityName: String = ""
    @State private var isEnrolling: Bool = false
    @State private var enrollError: String?

    var body: some View {
        VStack(spacing: 30) {
            // Header
            VStack(spacing: 8) {
                Image(systemName: "faceid")
                    .font(.system(size: 48))
                    .foregroundStyle(.blue)

                Text("Welcome to VisionSight")
                    .font(.system(size: 26, weight: .bold))

                Text("Biometric auto-unlock powered natively by Apple Neural Engine & Vision.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Step Content
            VStack {
                switch step {
                case 0:
                    permissionsStep
                case 1:
                    passwordStep
                default:
                    faceStep
                }
            }
            .frame(maxWidth: 500)
            .padding(24)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 16))

            Spacer()
        }
        .padding(40)
        .onAppear {
            appState.refreshPermissions()
            if appState.cameraAuthorized && appState.accessibilityAuthorized {
                if !appState.keychainPasswordExists {
                    step = 1
                } else {
                    step = 2
                }
            }
        }
    }

    // Step 0: Permissions
    private var permissionsStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("1. Required Permissions")
                .font(.headline)

            Text("VisionSight runs entirely offline on your Mac. It requires Camera permission to verify your face and Accessibility permission to post simulated keystrokes to the login window.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Divider()

            HStack {
                Label("Camera Access", systemImage: "camera")
                Spacer()
                if appState.cameraAuthorized {
                    Text("Granted").foregroundStyle(.green)
                } else {
                    Button("Grant Camera") {
                        Task {
                            _ = await CameraController.requestPermission()
                            appState.refreshPermissions()
                        }
                    }
                }
            }

            HStack {
                Label("Accessibility Tap", systemImage: "accessibility")
                Spacer()
                if appState.accessibilityAuthorized {
                    Text("Granted").foregroundStyle(.green)
                } else {
                    Button("Open Settings") {
                        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!)
                        appState.refreshPermissions()
                    }
                }
            }

            Divider()

            Button("Continue") {
                appState.refreshPermissions()
                step = 1
            }
            .buttonStyle(.borderedProminent)
            .disabled(!appState.cameraAuthorized || !appState.accessibilityAuthorized)
            .frame(maxWidth: .infinity, alignment: .trailing)
        }
    }

    // Step 1: Password
    private var passwordStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("2. Mac Login Password")
                .font(.headline)

            Text("To bypass the macOS Lock Screen upon face recognition, VisionSight needs your login password. It is encrypted in the native Apple Keychain and never written to disk.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            SecureField("Enter macOS Login Password...", text: $passwordInput)
                .textFieldStyle(.roundedBorder)

            Divider()

            Button("Save to Keychain & Continue") {
                guard !passwordInput.isEmpty else { return }
                try? KeychainManager.save(password: passwordInput)
                passwordInput = ""
                appState.refreshPermissions()
                step = 2
            }
            .buttonStyle(.borderedProminent)
            .disabled(passwordInput.isEmpty)
            .frame(maxWidth: .infinity, alignment: .trailing)
        }
    }

    // Step 2: Face
    private var faceStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("3. Register Your Face")
                .font(.headline)

            Text("Position yourself in front of the camera with good lighting, enter your name, and click Capture.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            TextField("Your Name (e.g. Rishi)", text: $identityName)
                .textFieldStyle(.roundedBorder)

            if let err = enrollError {
                Text(err).font(.caption).foregroundStyle(.red)
            }

            Divider()

            Button {
                captureAndFinish()
            } label: {
                if isEnrolling {
                    ProgressView().controlSize(.small)
                } else {
                    Text("Capture & Finish Setup")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(identityName.trimmingCharacters(in: .whitespaces).isEmpty || isEnrolling)
            .frame(maxWidth: .infinity, alignment: .trailing)
        }
    }

    private func captureAndFinish() {
        let name = identityName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }

        isEnrolling = true
        enrollError = nil

        Task {
            let camera = CameraController()
            guard let pixelBuffer = camera.capturePhoto() else {
                await MainActor.run {
                    enrollError = "Could not capture webcam frame."
                    isEnrolling = false
                }
                return
            }
            camera.stop()

            let engine = FaceEngine()
            do {
                let faces = try engine.detectFaces(in: pixelBuffer)
                guard faces.count == 1 else {
                    await MainActor.run {
                        enrollError = faces.isEmpty ? "No face detected." : "Multiple faces detected."
                        isEnrolling = false
                    }
                    return
                }

                guard let fp = try engine.generateFeaturePrint(from: pixelBuffer, face: faces[0]) else {
                    await MainActor.run {
                        enrollError = "Failed to generate feature print."
                        isEnrolling = false
                    }
                    return
                }

                let id = try Identity(name: name, featurePrint: fp)
                try IdentityStore.register(id)

                await MainActor.run {
                    appState.refreshIdentities()
                    appState.refreshPermissions()
                    if !appState.needsOnboarding {
                        appState.startDaemon()
                    }
                }
            } catch {
                await MainActor.run {
                    enrollError = error.localizedDescription
                    isEnrolling = false
                }
            }
        }
    }
}
