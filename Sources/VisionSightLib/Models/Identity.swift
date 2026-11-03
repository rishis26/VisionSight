import Foundation
import Vision

// MARK: - Identity

/// A registered face identity with stored biometric embedding.
///
/// Each identity stores a serialized `VNFeaturePrintObservation` that can be
/// compared against live camera feature prints for face recognition.
/// The feature print is archived via `NSKeyedArchiver` and stored as raw `Data`,
/// which `Codable` encodes as base-64 in JSON.
public struct Identity: Codable, Identifiable {

    /// Unique identifier for this identity.
    public let id: UUID

    /// Human-readable name (e.g. "John").
    public var name: String

    /// `NSKeyedArchiver`-serialized `VNFeaturePrintObservation`.
    public var featurePrintData: Data

    /// Optional photo file name stored in `AppPaths.facesDir` (e.g. "john.jpg").
    public var photoFileName: String?

    /// Timestamp when this identity was first registered.
    public var registeredAt: Date

    // MARK: Initializer

    /// Create a new identity from a live `VNFeaturePrintObservation`.
    public init(name: String, featurePrint: VNFeaturePrintObservation, photoFileName: String? = nil) throws {
        self.id = UUID()
        self.name = name
        self.featurePrintData = try NSKeyedArchiver.archivedData(
            withRootObject: featurePrint,
            requiringSecureCoding: true
        )
        self.photoFileName = photoFileName
        self.registeredAt = Date()
    }

    // MARK: Feature-print access

    /// Reconstruct the `VNFeaturePrintObservation` from the stored data.
    public func loadFeaturePrint() -> VNFeaturePrintObservation? {
        try? NSKeyedUnarchiver.unarchivedObject(
            ofClass: VNFeaturePrintObservation.self,
            from: featurePrintData
        )
    }
}

// MARK: - IdentityStore

public enum IdentityStore {

    // MARK: Read

    /// Load all registered identities from disk.
    public static func loadAll() -> [Identity] {
        let url = AppPaths.identitiesFile
        guard FileManager.default.fileExists(atPath: url.path) else { return [] }
        do {
            let data = try Data(contentsOf: url)
            return try JSONDecoder().decode([Identity].self, from: data)
        } catch {
            Logger.shared.warning("IdentityStore: failed to load identities – \(error.localizedDescription)")
            return []
        }
    }

    // MARK: Write

    /// Save the full list of identities to disk, replacing any existing file.
    public static func saveAll(_ identities: [Identity]) throws {
        let url = AppPaths.identitiesFile
        let dir = url.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601
        let data = try encoder.encode(identities)
        try data.write(to: url, options: .atomic)
    }

    // MARK: Convenience mutations

    /// Register a new identity by appending it to the store.
    public static func register(_ identity: Identity) throws {
        var all = loadAll()
        all.append(identity)
        try saveAll(all)
    }

    /// Remove the first identity whose name matches (case-insensitive).
    public static func remove(named name: String) throws {
        var all = loadAll()
        all.removeAll { $0.name.lowercased() == name.lowercased() }
        try saveAll(all)
    }
}
