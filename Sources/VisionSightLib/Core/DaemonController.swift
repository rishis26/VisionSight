// DaemonController.swift — Orchestrates the face-scan cycle on lock/wake events.
//
// Flow:
//   Screen Locked → pre-warm (no camera)
//   Display Wake + Locked → open camera → detect face → liveness → match → unlock
//   Screen Unlocked → abort scan

import Foundation
import CoreGraphics

/// Orchestrates the biometric scan cycle in response to macOS lock/wake events.
final class DaemonController {

    private weak var appState: AppState?
    private var isScanning: Bool = false
    private var scanTask: Task<Void, Never>?
    private var lastScanEnd: Date = .distantPast
    private var abortFlag: Bool = false

    init(appState: AppState) {
        self.appState = appState
    }

    // MARK: - Lifecycle

    func start() {
        guard let appState else { return }

        appState.lockMonitor.onScreenLocked = { [weak self] in
            Logger.shared.event("🔒 Screen Locked")
            self?.appState?.daemonState = .locked
        }

        appState.lockMonitor.onScreenWoke = { [weak self] in
            Logger.shared.event("☀️ Display Wake Detected")
            guard let self, let state = self.appState else { return }
            if state.lockMonitor.isScreenLocked() {
                Logger.shared.info("🔒 System is locked & display woke — starting face scan...")
                self.triggerScan()
            } else {
                Logger.shared.info("🔓 Display awake but Mac is already unlocked")
                state.daemonState = .idle
            }
        }

        appState.lockMonitor.onScreenUnlocked = { [weak self] in
            Logger.shared.event("🔓 Screen Unlocked")
            self?.abortScan()
            self?.appState?.daemonState = .idle
        }

        appState.lockMonitor.start()
        Logger.shared.info("🚀 DaemonController started — monitoring lock/wake events")
    }

    func stop() {
        abortScan()
        appState?.lockMonitor.stop()
        Logger.shared.info("DaemonController stopped")
    }

    // MARK: - Scan Orchestration

    private func triggerScan() {
        guard let appState else { return }

        // Cooldown check
        let elapsed = Date().timeIntervalSince(lastScanEnd)
        let cooldown = Double(appState.config.cooldownSeconds)
        if elapsed < cooldown {
            Logger.shared.info("⏱️ Scan cooldown active (\(String(format: "%.1f", elapsed))s / \(Int(cooldown))s) — skipping")
            appState.daemonState = .cooldown
            return
        }

        // Prevent overlapping scans
        guard !isScanning else {
            Logger.shared.info("Already scanning — ignoring duplicate trigger")
            return
        }

        appState.daemonState = .scanning
        isScanning = true
        abortFlag = false

        scanTask = Task { [weak self] in
            guard let self else { return }
            let result = await self.performScan()
            await MainActor.run {
                self.handleScanResult(result)
            }
        }
    }

    private func abortScan() {
        abortFlag = true
        scanTask?.cancel()
        scanTask = nil

        if isScanning {
            isScanning = false
            appState?.cameraController.stop()
            Logger.shared.info("🛑 Scan aborted")
        }
    }

    // MARK: - Core Scan Pipeline

    private func performScan() async -> (ScanResult, String?) {
        guard let appState else { return (.failed, nil) }

        let config = appState.config
        let camera = appState.cameraController
        let faceEngine = appState.faceEngine
        let livenessDetector = appState.livenessDetector
        let identities = appState.identities

        guard !identities.isEmpty else {
            Logger.shared.warning("No registered identities — cannot scan")
            return (.failed, nil)
        }

        // Start camera
        camera.start(
            cameraIndex: config.cameraIndex,
            width: config.resolution == .hd ? 1280 : 640,
            height: config.resolution == .hd ? 720 : 480
        )

        // Wait briefly for camera to warm up
        try? await Task.sleep(for: .milliseconds(200))

        let timeout = config.scanTimeoutSeconds
        let startTime = Date()

        Logger.shared.info("👁️ SCANNING: Waiting for authorized face...")

        while !abortFlag && !Task.isCancelled {
            // Timeout check
            if Date().timeIntervalSince(startTime) > Double(timeout) {
                camera.stop()
                return (.timeout, nil)
            }

            // Check if screen was unlocked externally
            if !appState.lockMonitor.isScreenLocked() {
                camera.stop()
                return (.aborted, nil)
            }

            // Grab a frame
            guard let pixelBuffer = await captureFrame(from: camera) else {
                try? await Task.sleep(for: .milliseconds(30))
                continue
            }

            // Detect faces
            let faces: [Any]  // VNFaceObservation
            do {
                let detected = try faceEngine.detectFaces(in: pixelBuffer)
                guard !detected.isEmpty else {
                    try? await Task.sleep(for: .milliseconds(30))
                    continue
                }
                faces = detected
            } catch {
                Logger.shared.error("Face detection error: \(error)")
                try? await Task.sleep(for: .milliseconds(100))
                continue
            }

            // Process each detected face
            for faceObs in faces {
                guard let face = faceObs as? VNFaceObservation else { continue }

                // Liveness check
                do {
                    let landmarked = try livenessDetector.detectLandmarks(
                        in: pixelBuffer, faces: [face]
                    )
                    guard let checked = landmarked.first else { continue }

                    if !livenessDetector.isAlive(observation: checked) {
                        Logger.shared.warning("⚠️ Liveness failed: eyes appear closed")
                        continue
                    }
                } catch {
                    Logger.shared.error("Liveness check error: \(error)")
                    continue
                }

                // Generate feature print
                guard let featurePrint = try? faceEngine.generateFeaturePrint(
                    from: pixelBuffer, face: face
                ) else {
                    continue
                }

                // Match against stored identities
                if let match = faceEngine.match(
                    featurePrint: featurePrint,
                    against: identities,
                    tolerance: Float(config.tolerance)
                ) {
                    Logger.shared.event("✅ Identity Verified: \(match.name) (distance: \(String(format: "%.3f", match.distance)))")

                    // Release camera before unlock (turn off LED first)
                    camera.stop()

                    // Perform unlock if enabled
                    if config.autoUnlock {
                        performUnlock(userName: match.name)
                    } else {
                        Logger.shared.info("✅ Access granted to \(match.name), but AUTO UNLOCK is disabled")
                    }

                    return (.success, match.name)
                }
            }

            try? await Task.sleep(for: .milliseconds(30))
        }

        camera.stop()
        return (abortFlag ? .aborted : .failed, nil)
    }

    /// Capture a single frame from the camera controller.
    private func captureFrame(from camera: CameraController) async -> CVPixelBuffer? {
        return await withCheckedContinuation { continuation in
            var received = false
            camera.onFrame = { buffer in
                guard !received else { return }
                received = true
                camera.onFrame = nil
                continuation.resume(returning: buffer)
            }

            // Timeout after 100ms if no frame arrives
            DispatchQueue.global().asyncAfter(deadline: .now() + 0.1) {
                guard !received else { return }
                received = true
                camera.onFrame = nil
                continuation.resume(returning: nil)
            }
        }
    }

    // MARK: - Unlock

    private func performUnlock(userName: String) {
        Logger.shared.info("Access Granted to \(userName). Waking Mac...")

        // Keep display awake
        UnlockInjector.keepDisplayAwake(seconds: 5)

        // Retrieve password from keychain
        guard let password = KeychainManager.retrieve() else {
            Logger.shared.error("⚠️ No password in Keychain — cannot unlock")
            return
        }

        // Inject keystrokes
        UnlockInjector.injectPassword(password)
        Logger.shared.event("✅ Unlock sequence dispatched for \(userName)")

        // Play unlock sound
        playUnlockSound()
    }

    private func playUnlockSound() {
        DispatchQueue.global(qos: .utility).async {
            let sounds = [
                "/System/Library/Sounds/Glass.aiff",
                "/System/Library/Sounds/Ping.aiff",
                "/System/Library/Sounds/Tink.aiff",
            ]
            guard let soundPath = sounds.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
                return
            }
            let task = Process()
            task.executableURL = URL(fileURLWithPath: "/usr/bin/afplay")
            task.arguments = [soundPath]
            try? task.run()
            task.waitUntilExit()
        }
    }

    // MARK: - Result Handling

    private func handleScanResult(_ result: (ScanResult, String?)) {
        isScanning = false
        lastScanEnd = Date()

        let (scanResult, authName) = result
        appState?.reportScanResult(scanResult, authName: authName)

        if scanResult != .aborted {
            appState?.daemonState = .cooldown

            // Return to idle after cooldown
            let cooldown = appState?.config.cooldownSeconds ?? 10
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(cooldown)) { [weak self] in
                if self?.appState?.daemonState == .cooldown {
                    self?.appState?.daemonState = .idle
                }
            }
        } else {
            appState?.daemonState = .idle
        }
    }
}

// MARK: - VNFaceObservation import
import Vision

