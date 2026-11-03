import Foundation

/// Centralized path management for VisionSight app data.
///
/// All application data lives under `~/Library/Application Support/VisionSight/`.
/// Call ``ensureDirectoriesExist()`` once at launch to guarantee the directory
/// tree is in place before any read/write operations.
public enum AppPaths {

    // MARK: - Root

    /// `~/Library/Application Support/VisionSight/`
    public static var appDataDir: URL {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!
        return appSupport.appendingPathComponent("VisionSight", isDirectory: true)
    }

    // MARK: - Asset Directories

    /// `~/Library/Application Support/VisionSight/assets/known_faces/`
    public static var facesDir: URL {
        appDataDir
            .appendingPathComponent("assets", isDirectory: true)
            .appendingPathComponent("known_faces", isDirectory: true)
    }

    // MARK: - Files

    /// `~/Library/Application Support/VisionSight/logs/daemon.log`
    public static var logFile: URL {
        appDataDir
            .appendingPathComponent("logs", isDirectory: true)
            .appendingPathComponent("daemon.log")
    }

    /// `~/Library/Application Support/VisionSight/config.json`
    public static var configFile: URL {
        appDataDir.appendingPathComponent("config.json")
    }

    /// `~/Library/Application Support/VisionSight/daemon.pid`
    public static var pidFile: URL {
        appDataDir.appendingPathComponent("daemon.pid")
    }

    /// `~/Library/Application Support/VisionSight/assets/known_faces/identities.json`
    public static var identitiesFile: URL {
        facesDir.appendingPathComponent("identities.json")
    }

    // MARK: - Directory Creation

    /// Create all necessary directories if they don't already exist.
    public static func ensureDirectoriesExist() {
        let fm = FileManager.default
        let directories = [
            appDataDir,
            facesDir,
            appDataDir.appendingPathComponent("logs", isDirectory: true),
        ]
        for dir in directories {
            try? fm.createDirectory(
                at: dir,
                withIntermediateDirectories: true,
                attributes: nil
            )
        }
    }
}
