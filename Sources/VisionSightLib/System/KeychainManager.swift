import Foundation
import Security

/// Hardware Keychain integration for secure password storage.
///
/// Passwords are stored under the service `com.visionsight.daemon` and keyed
/// to the current macOS user account via `NSUserName()`. All operations use
/// the Security.framework C API directly — no subprocess calls.
public enum KeychainManager {

    /// The Keychain service identifier for VisionSight.
    private static let service = "com.visionsight.daemon"

    /// Errors that can occur during Keychain operations.
    public enum KeychainError: LocalizedError {
        case encodingFailed
        case saveFailed(status: OSStatus)
        case deleteFailed(status: OSStatus)
        case unexpectedItemData

        public var errorDescription: String? {
            switch self {
            case .encodingFailed:
                return "Failed to encode password as UTF-8 data."
            case .saveFailed(let status):
                let msg = SecCopyErrorMessageString(status, nil) as String? ?? "Unknown"
                return "Keychain save failed (OSStatus \(status)): \(msg)"
            case .deleteFailed(let status):
                let msg = SecCopyErrorMessageString(status, nil) as String? ?? "Unknown"
                return "Keychain delete failed (OSStatus \(status)): \(msg)"
            case .unexpectedItemData:
                return "Unexpected data format returned from Keychain."
            }
        }
    }

    // MARK: - Public API

    /// Store a password securely in the macOS Keychain.
    public static func save(password: String) throws {
        guard let data = password.data(using: .utf8) else {
            throw KeychainError.encodingFailed
        }

        // Remove any existing item first to avoid errSecDuplicateItem.
        try? delete()

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: NSUserName(),
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.saveFailed(status: status)
        }
    }

    /// Retrieve the stored password from the Keychain.
    public static func retrieve() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: NSUserName(),
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let password = String(data: data, encoding: .utf8)
        else {
            return nil
        }
        return password
    }

    /// Delete the stored password from the Keychain.
    public static func delete() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: NSUserName(),
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.deleteFailed(status: status)
        }
    }

    /// Check if a password entry exists in the Keychain.
    public static func exists() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: NSUserName(),
            kSecReturnData as String: false,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]

        let status = SecItemCopyMatching(query as CFDictionary, nil)
        return status == errSecSuccess
    }
}
