import AppKit
import CoreGraphics
import Foundation
import Combine

/// Monitors macOS screen lock, unlock, sleep, and wake events.
///
/// Uses `DistributedNotificationCenter` for lock/unlock notifications and
/// `NSWorkspace.shared.notificationCenter` for sleep/wake events.
/// The ``isLocked`` property is observable and updated in real time.
///
/// Call ``start()`` to begin monitoring and ``stop()`` to tear down observers.
public final class LockMonitor: ObservableObject {

    // MARK: - Observable State

    /// Whether the screen is currently locked.
    @Published public var isLocked: Bool = false

    public init() {}

    // MARK: - Callbacks

    /// Called when the screen becomes locked.
    public var onScreenLocked: (() -> Void)?

    /// Called when the display wakes from sleep.
    public var onScreenWoke: (() -> Void)?

    /// Called when the screen is unlocked by the user.
    public var onScreenUnlocked: (() -> Void)?

    /// Called when the VisionSight GUI should be shown (via distributed notification).
    public var onShowGUI: (() -> Void)?

    // MARK: - Private Storage

    /// Observer tokens for `DistributedNotificationCenter`.
    private var distributedObservers: [NSObjectProtocol] = []

    /// Observer tokens for `NSWorkspace.shared.notificationCenter`.
    private var workspaceObservers: [NSObjectProtocol] = []

    // MARK: - Lifecycle

    /// Begin monitoring lock, unlock, sleep, and wake events.
    public func start() {
        stop()

        // Seed the initial lock state.
        isLocked = isScreenLocked()

        let distributed = DistributedNotificationCenter.default()

        let lockObserver = distributed.addObserver(
            forName: NSNotification.Name("com.apple.screenIsLocked"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.isLocked = true
            self?.onScreenLocked?()
        }
        distributedObservers.append(lockObserver)

        let unlockObserver = distributed.addObserver(
            forName: NSNotification.Name("com.apple.screenIsUnlocked"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.isLocked = false
            self?.onScreenUnlocked?()
        }
        distributedObservers.append(unlockObserver)

        let guiObserver = distributed.addObserver(
            forName: NSNotification.Name("com.visionsight.show_gui"),
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.onShowGUI?()
        }
        distributedObservers.append(guiObserver)

        let workspace = NSWorkspace.shared.notificationCenter

        let sleepObserver = workspace.addObserver(
            forName: NSWorkspace.screensDidSleepNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.isLocked = true
            self?.onScreenLocked?()
        }
        workspaceObservers.append(sleepObserver)

        let wakeObserver = workspace.addObserver(
            forName: NSWorkspace.screensDidWakeNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.onScreenWoke?()
        }
        workspaceObservers.append(wakeObserver)
    }

    /// Stop monitoring and remove all observers.
    public func stop() {
        let distributed = DistributedNotificationCenter.default()
        for observer in distributedObservers {
            distributed.removeObserver(observer)
        }
        distributedObservers.removeAll()

        let workspace = NSWorkspace.shared.notificationCenter
        for observer in workspaceObservers {
            workspace.removeObserver(observer)
        }
        workspaceObservers.removeAll()
    }

    // MARK: - Direct Query

    /// Query the current lock state via Quartz session properties.
    public func isScreenLocked() -> Bool {
        guard let sessionDict = CGSessionCopyCurrentDictionary() as? [String: Any] else {
            return false
        }
        return (sessionDict["CGSSessionScreenIsLocked"] as? Bool) ?? false
    }

    deinit {
        stop()
    }
}
