import Foundation

/// User-configurable settings, persisted as JSON in the app data directory.
///
/// Load the current settings with ``load()`` which returns defaults if no
/// configuration file exists yet. Mutate the struct and call ``save()``
/// to persist changes.
public struct Configuration: Codable {

    /// Index of the camera device to use for face capture (0 = default).
    public var cameraIndex: Int = 0

    /// Face recognition tolerance — lower values are stricter.
    /// A value of 0.55 is a reasonable default for most lighting conditions.
    public var tolerance: Double = 0.55

    /// Whether automatic unlock on face recognition is enabled.
    public var autoUnlock: Bool = true

    /// Minimum seconds to wait between consecutive unlock attempts.
    public var cooldownSeconds: Int = 10

    /// Maximum seconds to scan for a face before timing out.
    public var scanTimeoutSeconds: Int = 6

    /// Camera capture resolution.
    public var resolution: Resolution = .standard

    /// Supported camera capture resolutions.
    public enum Resolution: String, Codable, CaseIterable {
        case standard = "640x480"
        case hd = "1280x720"
    }

    public init(
        cameraIndex: Int = 0,
        tolerance: Double = 0.55,
        autoUnlock: Bool = true,
        cooldownSeconds: Int = 10,
        scanTimeoutSeconds: Int = 6,
        resolution: Resolution = .standard
    ) {
        self.cameraIndex = cameraIndex
        self.tolerance = tolerance
        self.autoUnlock = autoUnlock
        self.cooldownSeconds = cooldownSeconds
        self.scanTimeoutSeconds = scanTimeoutSeconds
        self.resolution = resolution
    }

    // MARK: - Persistence

    /// Load configuration from disk, or return defaults if no file exists.
    public static func load() -> Configuration {
        let url = AppPaths.configFile
        guard FileManager.default.fileExists(atPath: url.path) else {
            return Configuration()
        }
        do {
            let data = try Data(contentsOf: url)
            let config = try JSONDecoder().decode(Configuration.self, from: data)
            return config
        } catch {
            return Configuration()
        }
    }

    /// Save the current configuration to disk as pretty-printed JSON.
    public func save() throws {
        AppPaths.ensureDirectoriesExist()

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(self)
        try data.write(to: AppPaths.configFile, options: .atomic)
    }
}
