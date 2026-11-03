import SwiftUI
import VisionSightLib

struct SecurityView: View {
    @ObservedObject var appState: AppState
    @State private var newPassword: String = ""
    @State private var saveStatus: String?
    @State private var isError: Bool = false
    @State private var showResetConfirmation: Bool = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                Text("System Security & Keychain")
                    .font(.system(size: 28, weight: .bold))

                // Keychain Entry Section
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Image(systemName: "key.fill")
                            .foregroundStyle(.blue)
                        Text("HARDWARE KEYCHAIN ENCLAVE")
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)
                    }

                    Text("VisionSight encrypts your Mac login password directly in the macOS Keychain using Apple's Security framework. It is strictly localized to your machine and never leaves memory or touches disk.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    SecureField("Enter Mac Login Password...", text: $newPassword)
                        .textFieldStyle(.roundedBorder)

                    Button("Save to Keychain") {
                        savePassword()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(newPassword.isEmpty)

                    if let status = saveStatus {
                        Text(status)
                            .font(.caption)
                            .foregroundStyle(isError ? .red : .green)
                    }
                }
                .padding(20)
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                // Danger Zone
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Image(systemName: "exclamationmark.octagon.fill")
                            .foregroundStyle(.red)
                        Text("DANGER ZONE")
                            .font(.caption.bold())
                            .foregroundStyle(.red)
                    }

                    Text("Resetting erases all enrolled face profiles, audit logs, and your saved Mac password from the Keychain.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    Button("Reset All Biometric & Keychain Data", role: .destructive) {
                        showResetConfirmation = true
                    }
                    .buttonStyle(.bordered)
                }
                .padding(20)
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                Spacer()
            }
            .padding(30)
        }
        .confirmationDialog(
            "Are you sure you want to reset all data?",
            isPresented: $showResetConfirmation,
            titleVisibility: .visible
        ) {
            Button("Erase Everything", role: .destructive) {
                resetAll()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("This will permanently delete your Keychain password and enrolled facial identities.")
        }
    }

    private func savePassword() {
        guard !newPassword.isEmpty else { return }
        do {
            try KeychainManager.save(password: newPassword)
            newPassword = ""
            saveStatus = "Password securely saved to Apple Keychain!"
            isError = false
            appState.refreshPermissions()
        } catch {
            saveStatus = "Failed to save password: \(error.localizedDescription)"
            isError = true
        }
    }

    private func resetAll() {
        try? KeychainManager.delete()
        try? FileManager.default.removeItem(at: AppPaths.appDataDir)
        AppPaths.ensureDirectoriesExist()
        appState.refreshIdentities()
        appState.refreshPermissions()
        saveStatus = "All VisionSight data erased."
        isError = false
    }
}
