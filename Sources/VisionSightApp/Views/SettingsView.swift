import SwiftUI
import VisionSightLib

struct SettingsView: View {
    @ObservedObject var appState: AppState

    var body: some View {
        Form {
            Section("Biometrics") {
                Slider(
                    value: $appState.config.tolerance,
                    in: 0.35...0.75,
                    step: 0.05
                ) {
                    Text("Strictness Tolerance: \(String(format: "%.2f", appState.config.tolerance))")
                } minimumValueLabel: {
                    Text("Strict")
                } maximumValueLabel: {
                    Text("Relaxed")
                }
                Text("Lower values require closer facial matches; higher values permit subtle appearance variations.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section("Timing & Scan") {
                Stepper("Scan Timeout: \(appState.config.scanTimeoutSeconds) seconds", value: $appState.config.scanTimeoutSeconds, in: 2...15)
                Stepper("Cooldown Delay: \(appState.config.cooldownSeconds) seconds", value: $appState.config.cooldownSeconds, in: 3...30)
            }

            Section("Automation") {
                Toggle("Auto-Type Password on Match", isOn: $appState.config.autoUnlock)
                Text("When enabled, VisionSight types your macOS password into the login window immediately upon facial recognition.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section("Camera Device") {
                Picker("Resolution", selection: $appState.config.resolution) {
                    ForEach(Configuration.Resolution.allCases, id: \.self) { res in
                        Text(res.rawValue).tag(res)
                    }
                }
                Stepper("Camera Index: \(appState.config.cameraIndex)", value: $appState.config.cameraIndex, in: 0...5)
            }

            Section {
                Button("Save Settings") {
                    appState.saveConfiguration()
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .formStyle(.grouped)
        .padding(20)
    }
}
