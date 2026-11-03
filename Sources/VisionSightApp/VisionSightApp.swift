import SwiftUI
import VisionSightLib
import AppKit

@main
struct VisionSightApp: App {
    @StateObject private var appState = AppState()
    @Environment(\.openWindow) private var openWindow

    init() {
        AppPaths.ensureDirectoriesExist()
    }

    var body: some Scene {
        // ── 1. Native macOS Menu Bar Extra (Tray Item) ──────────────────────
        MenuBarExtra("VisionSight", systemImage: appState.isDaemonRunning ? "faceid" : "person.crop.circle.badge.xmark") {
            MenuBarView(appState: appState)
        }
        .menuBarExtraStyle(.window)

        // ── 2. Main Dashboard Window ─────────────────────────────────────────
        Window("VisionSight Dashboard", id: "dashboard") {
            Group {
                if appState.needsOnboarding {
                    OnboardingView(appState: appState)
                } else {
                    DashboardView(appState: appState)
                }
            }
            .frame(minWidth: 900, minHeight: 620)
            .background(Color(nsColor: .windowBackgroundColor))
            .onAppear {
                appState.refreshPermissions()
                appState.refreshIdentities()
                if !appState.needsOnboarding && !appState.isDaemonRunning {
                    appState.startDaemon()
                }

                // Listen for distributed notification from CLI `vs gui`
                DistributedNotificationCenter.default().addObserver(
                    forName: NSNotification.Name("com.visionsight.show_gui"),
                    object: nil,
                    queue: .main
                ) { _ in
                    NSApp.activate(ignoringOtherApps: true)
                }
            }
        }
        .windowResizability(.contentSize)

        // ── 3. Settings Scene ────────────────────────────────────────────────
        Settings {
            SettingsView(appState: appState)
                .frame(width: 500, height: 420)
        }
    }
}
