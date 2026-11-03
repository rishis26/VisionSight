import SwiftUI
import VisionSightLib

struct DashboardView: View {
    @ObservedObject var appState: AppState
    @State private var selectedTab: Tab = .overview

    enum Tab: String, CaseIterable, Identifiable {
        case overview = "Overview"
        case identities = "Identities"
        case settings = "Settings"
        case security = "Security"
        case logs = "Logs"

        var id: String { rawValue }
        var icon: String {
            switch self {
            case .overview: return "gauge.with.needle"
            case .identities: return "person.2.badge.gearshape"
            case .settings: return "slider.horizontal.3"
            case .security: return "lock.shield"
            case .logs: return "list.bullet.rectangle"
            }
        }
    }

    var body: some View {
        NavigationSplitView {
            List(Tab.allCases, selection: $selectedTab) { tab in
                NavigationLink(value: tab) {
                    Label(tab.rawValue, systemImage: tab.icon)
                }
            }
            .navigationSplitViewColumnWidth(min: 180, ideal: 200, max: 240)
            .toolbar {
                ToolbarItem {
                    Button {
                        appState.toggleDaemon()
                    } label: {
                        Label(
                            appState.isDaemonRunning ? "Stop Daemon" : "Start Daemon",
                            systemImage: appState.isDaemonRunning ? "stop.circle.fill" : "play.circle.fill"
                        )
                        .foregroundStyle(appState.isDaemonRunning ? .red : .green)
                    }
                }
            }
        } detail: {
            switch selectedTab {
            case .overview:
                OverviewTab(appState: appState)
            case .identities:
                IdentitiesView(appState: appState)
            case .settings:
                SettingsView(appState: appState)
            case .security:
                SecurityView(appState: appState)
            case .logs:
                LogsTabView()
            }
        }
    }
}

// MARK: - Overview Tab
struct OverviewTab: View {
    @ObservedObject var appState: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("System Overview")
                    .font(.system(size: 28, weight: .bold))

                HStack(spacing: 16) {
                    // Daemon State Card
                    StatusCard(
                        title: "DAEMON STATE",
                        value: appState.daemonState.rawValue,
                        subtitle: appState.isDaemonRunning ? "Monitoring screen lock/wake" : "Service stopped",
                        badgeColor: stateBadgeColor
                    )

                    // Last Auth Card
                    StatusCard(
                        title: "LAST EVENT",
                        value: appState.lastScanResult?.rawValue.uppercased() ?? "NO DATA",
                        subtitle: appState.lastScanTime != nil ? "\(appState.lastAuthName ?? "Unknown") • \(appState.lastScanTime!.formatted(date: .omitted, time: .shortened))" : "Awaiting scan trigger",
                        badgeColor: appState.lastScanResult == .success ? .green : .blue
                    )
                }

                // Quick Diagnostics Card
                VStack(alignment: .leading, spacing: 12) {
                    Text("SYSTEM HEALTH")
                        .font(.caption.bold())
                        .foregroundStyle(.secondary)

                    Divider()

                    HStack {
                        HealthRow(title: "Camera Access", ok: appState.cameraAuthorized)
                        Spacer()
                        HealthRow(title: "Accessibility HID Tap", ok: appState.accessibilityAuthorized)
                        Spacer()
                        HealthRow(title: "Hardware Keychain", ok: appState.keychainPasswordExists)
                    }
                }
                .padding(20)
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                // Registered Identities Summary
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("ACTIVE ENROLLMENTS")
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text("\(appState.identities.count) registered")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Divider()

                    if appState.identities.isEmpty {
                        Text("No face profiles enrolled yet. Switch to the Identities tab to register.")
                            .foregroundStyle(.secondary)
                            .font(.subheadline)
                    } else {
                        ForEach(appState.identities) { id in
                            HStack {
                                Image(systemName: "person.crop.circle.fill")
                                    .foregroundStyle(.blue)
                                Text(id.name)
                                    .font(.body.weight(.medium))
                                Spacer()
                                Text(id.registeredAt.formatted(date: .abbreviated, time: .omitted))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                .padding(20)
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 12))

                Spacer()
            }
            .padding(30)
        }
    }

    private var stateBadgeColor: Color {
        switch appState.daemonState {
        case .offline: return .gray
        case .idle: return .blue
        case .scanning: return .cyan
        case .cooldown: return .purple
        case .locked: return .orange
        }
    }
}

struct StatusCard: View {
    let title: String
    let value: String
    let subtitle: String
    let badgeColor: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.bold())
                .foregroundStyle(.secondary)

            Text(value)
                .font(.system(size: 26, weight: .bold))
                .foregroundStyle(badgeColor)

            Text(subtitle)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(20)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct HealthRow: View {
    let title: String
    let ok: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: ok ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .foregroundStyle(ok ? .green : .red)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.caption)
                Text(ok ? "Authorized" : "Action Required")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct LogsTabView: View {
    @State private var logs: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("System Audit Logs")
                    .font(.title2.bold())
                Spacer()
                Button("Refresh") {
                    loadLogs()
                }
            }

            TextEditor(text: .constant(logs))
                .font(.system(.body, design: .monospaced))
                .padding(8)
                .background(Color(nsColor: .controlBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .padding(24)
        .onAppear {
            loadLogs()
        }
    }

    private func loadLogs() {
        let url = AppPaths.logFile
        if let data = try? String(contentsOf: url, encoding: .utf8) {
            logs = data
        } else {
            logs = "No logs available."
        }
    }
}
