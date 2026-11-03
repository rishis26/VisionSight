// AppState.swift — Central observable state for VisionSight
// Coordinates all subsystems and exposes state to SwiftUI views.

import Foundation
import Combine
import AppKit

/// Scan outcome reported by the DaemonController.
public enum ScanResult: String {
    case success
    case failed
    case rejected
    case aborted
    case timeout
}

/// Overall daemon state displayed on the dashboard.
public enum DaemonState: String {
    case offline = "OFFLINE"
    case idle = "IDLE"
    case scanning = "SCANNING"
    case cooldown = "COOLDOWN"
    case locked = "LOCKED"
}

/// Central application state — observed by all SwiftUI views.
public final class AppState: ObservableObject {

    // MARK: - Published State

    @Published public var isDaemonRunning: Bool = false
    @Published public var daemonState: DaemonState = .offline
    @Published public var lastScanResult: ScanResult?
    @Published public var lastScanTime: Date?
    @Published public var lastAuthName: String?

    @Published public var identities: [Identity] = []
    @Published public var config: Configuration = .load()

    @Published public var cameraAuthorized: Bool = false
    @Published public var accessibilityAuthorized: Bool = false
    @Published public var keychainPasswordExists: Bool = false

    @Published public var currentStatusMessage: String = ""

    // MARK: - Subsystems (internal, not for views)

    let lockMonitor = LockMonitor()
    let cameraController = CameraController()
    let faceEngine = FaceEngine()
    let livenessDetector = LivenessDetector()
    private(set) var daemon: DaemonController?

    // MARK: - Lifecycle

    public init() {
        refreshIdentities()
        refreshPermissions()
    }

    // MARK: - Daemon Control

    /// Start the background daemon that monitors lock/wake events.
    public func startDaemon() {
        guard daemon == nil else { return }
        let d = DaemonController(appState: self)
        self.daemon = d
        d.start()
        isDaemonRunning = true
        daemonState = .idle
        Logger.shared.event("Daemon started")
    }

    /// Stop the background daemon.
    public func stopDaemon() {
        daemon?.stop()
        daemon = nil
        isDaemonRunning = false
        daemonState = .offline
        Logger.shared.event("Daemon stopped")
    }

    /// Toggle daemon on/off.
    public func toggleDaemon() {
        if isDaemonRunning {
            stopDaemon()
        } else {
            startDaemon()
        }
    }

    // MARK: - Identity Management

    public func refreshIdentities() {
        identities = IdentityStore.loadAll()
    }

    public func removeIdentity(named name: String) {
        do {
            try IdentityStore.remove(named: name)
            refreshIdentities()
            Logger.shared.info("Removed identity: \(name)")
        } catch {
            Logger.shared.error("Failed to remove identity '\(name)': \(error)")
        }
    }

    // MARK: - Permissions

    public func refreshPermissions() {
        cameraAuthorized = CameraController.isAuthorized
        accessibilityAuthorized = checkAccessibility()
        keychainPasswordExists = KeychainManager.exists()
    }

    /// Check if Accessibility permission is granted (required for CGEvent posting).
    private func checkAccessibility() -> Bool {
        // AXIsProcessTrusted() returns true if the app has Accessibility permission
        let trusted = AXIsProcessTrustedWithOptions(
            [kAXTrustedCheckOptionPrompt.takeRetainedValue(): false] as CFDictionary
        )
        return trusted
    }

    /// Whether onboarding is needed (missing permissions, password, or identities).
    public var needsOnboarding: Bool {
        !cameraAuthorized || !accessibilityAuthorized || !keychainPasswordExists || identities.isEmpty
    }

    // MARK: - Configuration

    public func saveConfiguration() {
        do {
            try config.save()
            Logger.shared.info("Configuration saved")
        } catch {
            Logger.shared.error("Failed to save configuration: \(error)")
        }
    }

    // MARK: - Scan Result Handling (called by DaemonController)

    func reportScanResult(_ result: ScanResult, authName: String? = nil) {
        lastScanResult = result
        lastScanTime = Date()
        lastAuthName = authName

        switch result {
        case .success:
            Logger.shared.event("✅ Identity Verified: \(authName ?? "unknown")")
        case .failed:
            Logger.shared.warning("⚠️ Scan failed — no match or camera error")
        case .rejected:
            Logger.shared.info("🛑 Scan rejected by user")
        case .aborted:
            Logger.shared.info("🛑 Scan aborted — screen unlocked externally")
        case .timeout:
            Logger.shared.info("⏱️ Scan timed out")
        }
    }
}

