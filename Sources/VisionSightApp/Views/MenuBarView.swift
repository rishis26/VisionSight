import SwiftUI
import VisionSightLib

struct MenuBarView: View {
    @ObservedObject var appState: AppState
    @Environment(\.openWindow) private var openWindow

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "faceid")
                    .font(.title2)
                    .foregroundStyle(.blue)
                VStack(alignment: .leading, spacing: 2) {
                    Text("VisionSight")
                        .font(.headline)
                    Text(appState.isDaemonRunning ? "Protection Active" : "Protection Inactive")
                        .font(.caption)
                        .foregroundStyle(appState.isDaemonRunning ? .green : .secondary)
                }
                Spacer()
                Toggle("", isOn: Binding(
                    get: { appState.isDaemonRunning },
                    set: { _ in appState.toggleDaemon() }
                ))
                .toggleStyle(.switch)
            }
            .padding(.bottom, 4)

            Divider()

            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text("State:")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(appState.daemonState.rawValue)
                        .font(.caption.bold())
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(stateColor.opacity(0.2))
                        .foregroundStyle(stateColor)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                }

                if let lastAuth = appState.lastAuthName {
                    HStack {
                        Text("Last Verified:")
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text(lastAuth)
                            .font(.caption.bold())
                    }
                }

                HStack {
                    Text("Identities:")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("\(appState.identities.count) registered")
                        .font(.caption)
                }
            }
            .font(.subheadline)

            Divider()

            Button {
                openWindow(id: "dashboard")
                NSApp.activate(ignoringOtherApps: true)
            } label: {
                Label("Open Dashboard", systemImage: "macwindow")
            }
            .buttonStyle(.plain)

            Button {
                NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
            } label: {
                Label("Settings...", systemImage: "gearshape")
            }
            .buttonStyle(.plain)

            Divider()

            Button("Quit VisionSight") {
                appState.stopDaemon()
                NSApp.terminate(nil)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.red)
        }
        .padding(16)
        .frame(width: 260)
    }

    private var stateColor: Color {
        switch appState.daemonState {
        case .offline: return .gray
        case .idle: return .blue
        case .scanning: return .cyan
        case .cooldown: return .purple
        case .locked: return .orange
        }
    }
}
