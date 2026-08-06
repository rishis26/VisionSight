"""
main.py — VisionSight Daemon Core (Signal-Based, Thread-Safe)
--------------------------------------------------------------
Architecture:
  Main thread   → PyQt6 QApplication event loop + GUI + QThread scan workers
  Daemon thread → CFRunLoopRunInMode loop, Cocoa OS notifications ONLY

The daemon thread NEVER calls cv2 or face_recognition.
When a lock/wake event is detected, it emits a Qt signal across the
thread boundary (Qt signals are thread-safe for cross-thread emission).
The main thread receives the signal and dispatches a QThread-based
camera scan worker — which is safe for cv2.VideoCapture on Apple Silicon.

macOS Sonoma safe. PyInstaller arm64 safe. Single process.
"""

import time
import threading

import objc
from Foundation import (
    NSDistributedNotificationCenter,
    NSObject,
    NSNotificationSuspensionBehaviorDeliverImmediately,
    NSProcessInfo,
    NSActivityLatencyCritical,
    NSActivityUserInitiatedAllowingIdleSystemSleep,
)
from AppKit import (
    NSWorkspace,
    NSWorkspaceScreensDidSleepNotification,
    NSWorkspaceScreensDidWakeNotification,
    NSWorkspaceWillSleepNotification,
    NSWorkspaceDidWakeNotification,
)
from CoreFoundation import CFRunLoopRunInMode, kCFRunLoopDefaultMode
from PyQt6.QtCore import QObject, pyqtSignal

from system.lock import SystemController


# ── Qt Signal Bridge ───────────────────────────────────────────────────────────

class DaemonBridge(QObject):
    """
    Thread-safe Qt signal bridge between the Cocoa notification thread
    and PyQt6's main thread.

    Qt signal/slot connections default to AutoConnection, which means:
    - If emitter and receiver are on different threads, the slot call
      is QUEUED onto the receiver's event loop — fully thread-safe.
    - No mutex, no polling needed.
    """

    # → main thread: start a camera + face-recognition scan
    scan_requested = pyqtSignal()

    # → main thread: abort any currently active scan immediately
    abort_requested = pyqtSignal()

    # → main thread: show and raise the GUI window
    show_gui_requested = pyqtSignal()

    # → main thread: display is asleep while locked — pre-warm the scan subprocess
    #   (imports Python + dlib in the background, NO camera opened)
    warm_subprocess_requested = pyqtSignal()


# ── Cocoa Notification Listener ───────────────────────────────────────────────

class OSNotificationListener(NSObject):
    """
    Receives macOS OS-level broadcast notifications on the daemon thread.

    CRITICAL: This class NEVER touches cv2, face_recognition, or VideoCapture.
    It only checks the system lock state and emits Qt signals for the
    main thread to handle.
    """

    def initWithBridge_(self, bridge: DaemonBridge):
        self = objc.super(OSNotificationListener, self).init()
        if self:
            self._bridge = bridge
            # SystemController uses Quartz + subprocess — safe on any thread
            self._system = SystemController()
        return self

    def screenLocked_(self, notification):
        print("\n🔒 [OS EVENT] Screen Locked.")
        # Start pre-warming the scan subprocess NOW while the lock screen is
        # still visible and the display is on.  dlib (~5s import) loads in the
        # background so by the time the display wakes, only camera init remains.
        # NO camera is opened here — camera LED stays off until display wakes.
        print("🔄 Pre-warming scan worker (dlib will be ready before display wakes)...")
        self._bridge.warm_subprocess_requested.emit()

    def screenAwake_(self, notification):
        print("\n☀️ [OS EVENT] Display Wake Detected.")
        if self._system._is_macos_locked():
            idle_seconds = self._system.get_seconds_since_last_input()
            print(f"⏱️ Time since last user physical touch: {idle_seconds:.2f}s")
            # If the screen woke due to a push notification without any user touch,
            # idle_seconds will typically be > 1.5s - 2.0s.
            if idle_seconds > 2.0:
                print("🔕 Passive wake detected (e.g. notification banner without touch) — camera stays off until user touches laptop.")
                return

            print("🔒 System is locked & physical user touch detected — starting face scan...")
            self._bridge.scan_requested.emit()

    def screenUnlocked_(self, notification):
        print("\n🔓 [OS EVENT] Screen Unlocked externally.")
        self._bridge.abort_requested.emit()

    def showGUI_(self, notification):
        print("\n🖥️ [OS EVENT] Received show GUI notification. Emitting show_gui_requested...")
        self._bridge.show_gui_requested.emit()

    def screenAsleep_(self, notification):
        print("\n💤 [OS EVENT] Display Sleep Detected.")
        self._bridge.abort_requested.emit()
        # If screen is locked, pre-warm the scan subprocess NOW while the display
        # is asleep. The subprocess imports Python + dlib in the background.
        # NO camera is opened — camera only opens when the actual scan starts.
        if self._system._is_macos_locked():
            print("🔒 Screen locked during sleep — pre-warming scan worker...")
            self._bridge.warm_subprocess_requested.emit()


# ── Daemon Core ────────────────────────────────────────────────────────────────

class DaemonCore:
    """
    Manages the lifecycle of the background Cocoa notification listener thread.

    Usage (always from the main/GUI thread):
        core = DaemonCore()          # creates bridge QObject on main thread
        core.start()                 # spawns background listener thread
        core.stop()                  # signals clean shutdown
        core.is_alive() -> bool
        core.bridge.scan_requested.connect(my_slot)
        core.bridge.abort_requested.connect(my_abort_slot)
    """

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._activity = None

        # DaemonBridge QObject MUST be created on the main thread so Qt assigns
        # it to the main thread's event loop — this is what makes cross-thread
        # signal delivery work correctly.
        self.bridge = DaemonBridge()

    def start(self):
        """Start the Cocoa notification listener on a background daemon thread."""
        if self._thread and self._thread.is_alive():
            print("⚠️ DaemonCore: already running — ignoring start().")
            return

        # Prevent macOS App Nap from freezing or throttling the background daemon
        try:
            options = NSActivityUserInitiatedAllowingIdleSystemSleep | NSActivityLatencyCritical
            self._activity = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
                options,
                "VisionSight Biometric Security Daemon (Active Wake & Lock Listener)"
            )
            print("⚡ App Nap prevention active: Real-time OS event delivery guaranteed.")
        except Exception as e:
            print(f"⚠️ Could not set NSProcessInfo activity: {e}")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="VisionSightDaemonThread",
            daemon=True,  # Dies automatically when the process exits
        )
        self._thread.start()
        print("🚀 DaemonCore: background listener thread started.")

    def stop(self):
        """Signal the daemon thread to stop and wait for clean exit (max 5s)."""
        if self._activity:
            try:
                NSProcessInfo.processInfo().endActivity_(self._activity)
            except Exception:
                pass
            self._activity = None

        if not self._thread or not self._thread.is_alive():
            return

        print("🛑 DaemonCore: stopping listener thread...")
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        if self._thread.is_alive():
            print("⚠️ DaemonCore: thread did not exit cleanly within timeout.")
        else:
            print("✅ DaemonCore: thread exited cleanly.")
        self._thread = None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        """
        Body of the background daemon thread.

        Responsibilities:
          1. Register Cocoa notification observers
          2. Drive the NSRunLoop via CFRunLoopRunInMode() in 0.1s slices
          3. Clean up observers on stop
        """
        print("=" * 52)
        print("🚀 VISIONSIGHT DAEMON (SIGNAL-BRIDGE, THREAD MODE)")
        print("=" * 52)

        # All Cocoa objects are created here, on this thread's autorelease pool
        listener = OSNotificationListener.alloc().initWithBridge_(self.bridge)

        # 1. Lock / Unlock (distributed notifications with DeliverImmediately)
        dist_nc = NSDistributedNotificationCenter.defaultCenter()
        dist_nc.addObserver_selector_name_object_suspensionBehavior_(
            listener,
            "screenLocked:",
            "com.apple.screenIsLocked",
            None,
            NSNotificationSuspensionBehaviorDeliverImmediately,
        )
        dist_nc.addObserver_selector_name_object_suspensionBehavior_(
            listener,
            "screenUnlocked:",
            "com.apple.screenIsUnlocked",
            None,
            NSNotificationSuspensionBehaviorDeliverImmediately,
        )
        dist_nc.addObserver_selector_name_object_suspensionBehavior_(
            listener,
            "showGUI:",
            "com.visionsight.show_gui",
            None,
            NSNotificationSuspensionBehaviorDeliverImmediately,
        )

        # 2. Display Sleep / Wake AND System Deep Sleep / Lid Wake (workspace notifications)
        workspace_nc = NSWorkspace.sharedWorkspace().notificationCenter()
        workspace_nc.addObserver_selector_name_object_(
            listener,
            "screenAsleep:",
            NSWorkspaceScreensDidSleepNotification,
            None,
        )
        workspace_nc.addObserver_selector_name_object_(
            listener,
            "screenAwake:",
            NSWorkspaceScreensDidWakeNotification,
            None,
        )
        workspace_nc.addObserver_selector_name_object_(
            listener,
            "screenAsleep:",
            NSWorkspaceWillSleepNotification,
            None,
        )
        workspace_nc.addObserver_selector_name_object_(
            listener,
            "screenAwake:",
            NSWorkspaceDidWakeNotification,
            None,
        )

        print("✅ Daemon Ready. Listening for OS broadcasts (0% CPU idle)...")

        # Drive the run-loop in slices, with a time.sleep() to prevent a busy loop
        # on background threads (which otherwise return immediately from CFRunLoopRunInMode
        # when no sources/timers are registered on that thread's run-loop, consuming 100% CPU).
        last_touch_check = 0.0
        try:
            while not self._stop_event.is_set():
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, False)
                time.sleep(0.1)

                # If the screen is awake and locked, check for user physical touch
                # (covers case where notification woke screen earlier and user now touches keyboard/trackpad)
                now = time.time()
                if now - last_touch_check > 0.3:
                    last_touch_check = now
                    if listener._system._is_macos_locked() and listener._system._is_display_on():
                        idle_sec = listener._system.get_seconds_since_last_input()
                        if idle_sec < 0.4:
                            self.bridge.scan_requested.emit()
        except Exception as e:
            print(f"⚠️ DaemonCore run-loop exception: {e}")
        finally:
            dist_nc.removeObserver_(listener)
            workspace_nc.removeObserver_(listener)
            print("🛑 DaemonCore: run-loop exited. Observers removed.")


# ── Standalone entry-point (dev / debug only) ─────────────────────────────────
if __name__ == "__main__":
    import sys
    import signal
    from PyQt6.QtWidgets import QApplication

    qt_app = QApplication(sys.argv)

    core = DaemonCore()

    # In standalone mode, just print the signals — no camera scan
    core.bridge.scan_requested.connect(
        lambda: print("[STANDALONE] scan_requested signal received")
    )
    core.bridge.abort_requested.connect(
        lambda: print("[STANDALONE] abort_requested signal received")
    )

    core.start()

    def _handle_sigint(sig, frame):
        print("\n🛑 SIGINT received. Shutting down...")
        core.stop()
        qt_app.quit()

    signal.signal(signal.SIGINT, _handle_sigint)
    sys.exit(qt_app.exec())