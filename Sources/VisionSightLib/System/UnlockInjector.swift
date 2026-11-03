import CoreGraphics
import Foundation

/// Injects keystrokes at the HID level to unlock the macOS lock screen.
///
/// Uses `CGEvent` to simulate physical key presses, posting them directly
/// to the HID event tap. Requires Accessibility permissions to function.
///
/// The unlock sequence:
/// 1. Press Shift to wake the password field (avoids injecting a visible character)
/// 2. Type each character of the password via Unicode key events
/// 3. Press Return to submit the password
enum UnlockInjector {

    // MARK: - Virtual Keycodes

    /// Shift key virtual keycode.
    private static let kVK_Shift: CGKeyCode = 56

    /// Return key virtual keycode.
    private static let kVK_Return: CGKeyCode = 36

    /// Placeholder keycode used for Unicode character injection.
    private static let kVK_ANSI_A: CGKeyCode = 0

    // MARK: - Public API

    /// Simulate typing the password on the lock screen.
    ///
    /// This method blocks the calling thread for the duration of the injection
    /// (typically under 200ms for a 20-character password). It must be called
    /// from a context with Accessibility privileges.
    ///
    /// - Parameter password: The plaintext password to type.
    static func injectPassword(_ password: String) {
        guard let source = CGEventSource(stateID: .privateState) else {
            return
        }

        let tap = CGEventTapLocation.cghidEventTap

        // 1. Press Shift to wake the password field without injecting a space.
        postKey(keyCode: kVK_Shift, keyDown: true, source: source, tap: tap)
        postKey(keyCode: kVK_Shift, keyDown: false, source: source, tap: tap)
        usleep(50_000) // 50ms — give the login window time to focus the field

        // 2. Type each character of the password.
        for character in password {
            typeCharacter(character, source: source, tap: tap)
            usleep(3_000) // 3ms between key events
        }

        // 3. Brief pause, then press Return to submit.
        usleep(20_000) // 20ms before Return
        postKey(keyCode: kVK_Return, keyDown: true, source: source, tap: tap)
        postKey(keyCode: kVK_Return, keyDown: false, source: source, tap: tap)
    }

    /// Keep the display awake for a specified duration.
    ///
    /// Spawns `caffeinate -u -t <seconds>` as a detached process. The `-u`
    /// flag declares that the user is active, preventing the display from
    /// dimming or sleeping.
    ///
    /// - Parameter seconds: Number of seconds to keep the display awake (default 5).
    static func keepDisplayAwake(seconds: Int = 5) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/caffeinate")
        process.arguments = ["-u", "-t", "\(seconds)"]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        try? process.run()
        // Intentionally not waiting — let caffeinate run in the background.
    }

    // MARK: - Private Helpers

    /// Post a single key-down or key-up event.
    private static func postKey(
        keyCode: CGKeyCode,
        keyDown: Bool,
        source: CGEventSource,
        tap: CGEventTapLocation
    ) {
        guard let event = CGEvent(
            keyboardEventSource: source,
            virtualKey: keyCode,
            keyDown: keyDown
        ) else {
            return
        }
        event.post(tap: tap)
    }

    /// Type a single Unicode character by setting the Unicode string on a
    /// keyboard event pair (key-down + key-up).
    private static func typeCharacter(
        _ character: Character,
        source: CGEventSource,
        tap: CGEventTapLocation
    ) {
        var utf16Units = Array(String(character).utf16)

        // Key down
        guard let keyDown = CGEvent(
            keyboardEventSource: source,
            virtualKey: kVK_ANSI_A,
            keyDown: true
        ) else {
            return
        }
        keyDown.keyboardSetUnicodeString(
            stringLength: utf16Units.count,
            unicodeString: &utf16Units
        )
        keyDown.post(tap: tap)

        // Key up
        guard let keyUp = CGEvent(
            keyboardEventSource: source,
            virtualKey: kVK_ANSI_A,
            keyDown: false
        ) else {
            return
        }
        keyUp.keyboardSetUnicodeString(
            stringLength: utf16Units.count,
            unicodeString: &utf16Units
        )
        keyUp.post(tap: tap)
    }
}
