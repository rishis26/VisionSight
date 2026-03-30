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
from Foundation import NSDistributedNotificationCenter, NSObject
from AppKit import (
    NSWorkspace,
    NSWorkspaceScreensDidSleepNotification,
    NSWorkspaceScreensDidWakeNotification,
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
        print("\n🔒 [OS EVENT] Screen Locked. Waiting for display wake...")

    def screenAwake_(self, notification):
        print("\n☀️ [OS EVENT] Display Wake Detected.")
        if self._system._is_macos_locked():
            print("🔒 System is locked — signalling main thread to start scan...")
            self._bridge.scan_requested.emit()

    def screenUnlocked_(self, notification):
        print("\n🔓 [OS EVENT] Screen Unlocked externally.")
        self._bridge.abort_requested.emit()

    def screenAsleep_(self, notification):
        print("\n💤 [OS EVENT] Display Sleep Detected.")
        self._bridge.abort_requested.emit()


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

        # DaemonBridge QObject MUST be created on the main thread so Qt assigns
        # it to the main thread's event loop — this is what makes cross-thread
        # signal delivery work correctly.
        self.bridge = DaemonBridge()

    def start(self):
        """Start the Cocoa notification listener on a background daemon thread."""
        if self._thread and self._thread.is_alive():
            print("⚠️ DaemonCore: already running — ignoring start().")
            return

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
          2. Drive the NSRunLoop via CFRunLoopRunInMode() in 0.5s slices
          3. Clean up observers on stop

        NOT responsible for:
          - cv2 / VideoCapture (main thread via QThread)
          - face_recognition (main thread via QThread)
          - Scan state / cooldown (managed by GUI class)
        """
        print("=" * 52)
        print("🚀 VISIONSIGHT DAEMON (SIGNAL-BRIDGE, THREAD MODE)")
        print("=" * 52)

        # All Cocoa objects are created here, on this thread's autorelease pool
        listener = OSNotificationListener.alloc().initWithBridge_(self.bridge)

        # 1. Lock / Unlock (distributed notifications)
        dist_nc = NSDistributedNotificationCenter.defaultCenter()
        dist_nc.addObserver_selector_name_object_(
            listener, "screenLocked:", "com.apple.screenIsLocked", None
        )
        dist_nc.addObserver_selector_name_object_(
            listener, "screenUnlocked:", "com.apple.screenIsUnlocked", None
        )

        # 2. Display Sleep / Wake (workspace notifications)
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

        print("✅ Daemon Ready. Listening for OS broadcasts (0% CPU idle)...")

        # Drive the run-loop in 0.5s slices so _stop_event is checked regularly.
        # This replaces the blocking AppHelper.runEventLoop() call.
        try:
            while not self._stop_event.is_set():
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.5, False)
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