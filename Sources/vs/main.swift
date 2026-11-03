import Foundation
import VisionSightLib
import CoreGraphics
import Vision

@main
struct VSCLI {
    static func main() async {
        let args = CommandLine.arguments

        if args.count < 2 {
            printUsage()
            return
        }

        let command = args[1].lowercased()

        switch command {
        case "status":
            printStatus()
        case "list":
            listIdentities()
        case "register":
            if args.count < 3 {
                print("❌ Error: Name required.")
                print("Usage: vs register <name>")
                exit(1)
            }
            await registerFace(name: args[2])
        case "remove", "delete":
            if args.count < 3 {
                print("❌ Error: Name required.")
                print("Usage: vs remove <name>")
                exit(1)
            }
            removeIdentity(name: args[2])
        case "test":
            await testRecognition()
        case "setup":
            setupKeychainPassword()
        case "config":
            handleConfig(Array(args.dropFirst(2)))
        case "logs":
            viewLogs()
        case "gui":
            launchGUI()
        case "install":
            installGlobal()
        case "uninstall":
            uninstallAll()
        case "--version", "-v", "version":
            print("VisionSight Swift Version 6.0")
        case "--help", "-h", "help":
            printUsage()
        default:
            print("Unknown command: \(command)")
            printUsage()
            exit(1)
        }
    }

    static func printUsage() {
        print("""
        VisionSight CLI (Swift Native)
        Usage:
          vs status           Show system lock state & registered identities
          vs list             List all registered identities
          vs register <name>  Register a new face from the webcam
          vs remove <name>    Remove a registered identity
          vs test             Perform a one-time face recognition test
          vs setup            Save your Mac login password to macOS Keychain
          vs config           View or modify settings
          vs logs             View recent audit log entries
          vs gui              Open the VisionSight dashboard GUI
          vs install          Install 'vs' binary to /usr/local/bin
          vs uninstall        Erase all data and uninstall
        """)
    }

    static func printStatus() {
        let monitor = LockMonitor()
        let isLocked = monitor.isScreenLocked()
        let identities = IdentityStore.loadAll()
        let hasPassword = KeychainManager.exists()

        print("═══════════════════════════════════════")
        print("  VisionSight System Status (Native)   ")
        print("═══════════════════════════════════════")
        print("Screen Locked:       \(isLocked ? "🔒 YES" : "🔓 NO")")
        print("Keychain Password:   \(hasPassword ? "✅ Configured" : "❌ Missing (run 'vs setup')")")
        print("Camera Authorized:   \(CameraController.isAuthorized ? "✅ Yes" : "❌ No")")
        print("Identities Enrolled: \(identities.count)")
        for id in identities {
            print("  • \(id.name)")
        }
        print("═══════════════════════════════════════")
    }

    static func listIdentities() {
        let identities = IdentityStore.loadAll()
        if identities.isEmpty {
            print("No registered identities found.")
            return
        }
        print("Registered Identities (\(identities.count)):")
        for id in identities {
            print("  - \(id.name) (enrolled: \(id.registeredAt.formatted()))")
        }
    }

    static func registerFace(name: String) async {
        print("📸 Preparing to register face for '\(name)'...")
        print("Position yourself in front of the camera and look directly at the lens.")
        print("Press Enter when ready...")
        _ = readLine()

        print("Opening camera...")
        let camera = CameraController()
        guard let pixelBuffer = camera.capturePhoto() else {
            print("❌ Error: Failed to capture camera frame.")
            return
        }
        camera.stop()

        print("Analyzing facial features with Apple Vision...")
        let engine = FaceEngine()
        do {
            let faces = try engine.detectFaces(in: pixelBuffer)
            if faces.isEmpty {
                print("❌ Error: No face detected. Check lighting and position.")
                return
            }
            if faces.count > 1 {
                print("❌ Error: Multiple faces detected (\(faces.count)). Only one face allowed.")
                return
            }

            guard let featurePrint = try engine.generateFeaturePrint(from: pixelBuffer, face: faces[0]) else {
                print("❌ Error: Could not generate face embedding.")
                return
            }

            let identity = try Identity(name: name, featurePrint: featurePrint)
            try IdentityStore.register(identity)
            print("✅ Success! Identity '\(name)' securely registered.")
        } catch {
            print("❌ Registration failed: \(error.localizedDescription)")
        }
    }

    static func removeIdentity(name: String) {
        do {
            try IdentityStore.remove(named: name)
            print("✅ Identity '\(name)' removed.")
        } catch {
            print("❌ Failed to remove identity: \(error.localizedDescription)")
        }
    }

    static func testRecognition() async {
        let identities = IdentityStore.loadAll()
        guard !identities.isEmpty else {
            print("❌ No registered identities. Run 'vs register <name>' first.")
            return
        }

        print("👁️ Starting face recognition test (look at the camera)...")
        let camera = CameraController()
        guard let pixelBuffer = camera.capturePhoto() else {
            print("❌ Camera error.")
            return
        }
        camera.stop()

        let engine = FaceEngine()
        let config = Configuration.load()
        do {
            let faces = try engine.detectFaces(in: pixelBuffer)
            guard let firstFace = faces.first else {
                print("⚠️ No face found in frame.")
                return
            }

            guard let featurePrint = try engine.generateFeaturePrint(from: pixelBuffer, face: firstFace) else {
                print("⚠️ Could not generate feature print.")
                return
            }

            if let match = engine.match(featurePrint: featurePrint, against: identities, tolerance: Float(config.tolerance)) {
                print("✅ Authenticated as: \(match.name) (Confidence Distance: \(String(format: "%.3f", match.distance)))")
            } else {
                print("❌ Face detected but does not match any registered identity.")
            }
        } catch {
            print("❌ Recognition error: \(error.localizedDescription)")
        }
    }

    static func setupKeychainPassword() {
        print("═══════════════════════════════════════")
        print("  🔐 VisionSight Hardware Keychain Setup")
        print("═══════════════════════════════════════")
        print("Enter your Mac Login Password to enable biometric auto-unlock.")
        print("Stored natively in Apple Keychain (never touches disk/argv):")

        guard let pass = String(validatingUTF8: getpass("Password: ")) else {
            print("❌ Invalid password.")
            return
        }

        guard !pass.isEmpty else {
            print("❌ Password cannot be empty.")
            return
        }

        do {
            try KeychainManager.save(password: pass)
            print("✅ Password successfully saved into macOS Keychain!")
        } catch {
            print("❌ Failed to save password: \(error.localizedDescription)")
        }
    }

    static func handleConfig(_ args: [String]) {
        var config = Configuration.load()
        if args.isEmpty || args[0] == "list" {
            print("Current Configuration:")
            print("  Camera Index:     \(config.cameraIndex)")
            print("  Tolerance:        \(config.tolerance)")
            print("  Auto Unlock:      \(config.autoUnlock)")
            print("  Cooldown:         \(config.cooldownSeconds)s")
            print("  Scan Timeout:     \(config.scanTimeoutSeconds)s")
            print("  Resolution:       \(config.resolution.rawValue)")
        } else if args[0] == "set" && args.count >= 3 {
            let key = args[1].lowercased()
            let val = args[2]

            switch key {
            case "camera":
                if let idx = Int(val) { config.cameraIndex = idx }
            case "tolerance":
                if let tol = Double(val) { config.tolerance = tol }
            case "autounlock", "auto_unlock":
                config.autoUnlock = (val.lowercased() == "true" || val == "1")
            case "cooldown":
                if let s = Int(val) { config.cooldownSeconds = s }
            case "timeout":
                if let t = Int(val) { config.scanTimeoutSeconds = t }
            case "resolution":
                if let res = Configuration.Resolution(rawValue: val) { config.resolution = res }
            default:
                print("Unknown config key: \(key)")
                return
            }

            try? config.save()
            print("✅ Config updated: \(key) = \(val)")
        }
    }

    static func viewLogs() {
        let logUrl = AppPaths.logFile
        guard FileManager.default.fileExists(atPath: logUrl.path),
              let content = try? String(contentsOf: logUrl, encoding: .utf8) else {
            print("No log file found.")
            return
        }
        let lines = content.components(separatedBy: .newlines)
        print("Recent logs (last 20 lines):")
        for line in lines.suffix(20) where !line.isEmpty {
            print(line)
        }
    }

    static func launchGUI() {
        DistributedNotificationCenter.default().postNotificationName(
            NSNotification.Name("com.visionsight.show_gui"),
            object: nil,
            userInfo: nil,
            deliverImmediately: true
        )
        print("Signal sent to bring VisionSight GUI to front.")
    }

    static func installGlobal() {
        let execUrl = Bundle.main.executableURL ?? URL(fileURLWithPath: CommandLine.arguments[0])
        let dest = "/usr/local/bin/vs"
        print("Installing vs binary to \(dest)...")
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/sudo")
        task.arguments = ["cp", "-f", execUrl.path, dest]
        try? task.run()
        task.waitUntilExit()
        if task.terminationStatus == 0 {
            print("✅ 'vs' CLI installed globally. Run 'vs' anywhere!")
        } else {
            print("⚠️ Install failed (exit code \(task.terminationStatus)).")
        }
    }

    static func uninstallAll() {
        print("Type 'uninstall' to confirm deletion of all VisionSight data:")
        guard let confirmation = readLine(), confirmation.trimmingCharacters(in: .whitespaces).lowercased() == "uninstall" else {
            print("Cancelled.")
            return
        }

        try? KeychainManager.delete()
        try? FileManager.default.removeItem(at: AppPaths.appDataDir)
        print("✅ Keychain and app data erased.")
    }
}

