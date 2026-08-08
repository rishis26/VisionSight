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


class DaemonBridge(QObject):
    scan_requested = pyqtSignal()
    abort_requested = pyqtSignal()
    show_gui_requested = pyqtSignal()
    warm_subprocess_requested = pyqtSignal()


class OSNotificationListener(NSObject):

    def initWithBridge_(self, bridge: DaemonBridge):
        self = objc.super(OSNotificationListener, self).init()
        if self:
            self._bridge = bridge
            self._system = SystemController()
            self._waiting_for_touch = False
        return self

    def screenLocked_(self, notification):
        try:
            print("\n🔒 [OS EVENT] Screen Locked.")
            self._waiting_for_touch = False
            print("🔄 Pre-warming scan worker...")
            self._bridge.warm_subprocess_requested.emit()
        except Exception as e:
            print(f"⚠️ Error in screenLocked_ handler: {e}")

    def screenAwake_(self, notification):
        try:
            print("\n☀️ [OS EVENT] Display Wake Detected.")
            if self._system._is_macos_locked():
                idle_seconds = self._system.get_seconds_since_last_input()
                print(f"⏱️ Time since last user physical touch: {idle_seconds:.2f}s")
                # If the screen woke within 6 seconds of a user input (key, trackpad, lid), start scan immediately
                if idle_seconds > 6.0:
                    print("🔕 Passive wake detected (>6s idle) — waiting for user touch.")
                    self._waiting_for_touch = True
                    return

                self._waiting_for_touch = False
                print("🔒 System locked & user wake detected — starting scan...")
                self._bridge.scan_requested.emit()
        except Exception as e:
            print(f"⚠️ Error in screenAwake_ handler: {e}")

    def screenUnlocked_(self, notification):
        try:
            print("\n🔓 [OS EVENT] Screen Unlocked.")
            self._waiting_for_touch = False
            self._bridge.abort_requested.emit()
        except Exception as e:
            print(f"⚠️ Error in screenUnlocked_ handler: {e}")

    def showGUI_(self, notification):
        try:
            print("\n🖥️ [OS EVENT] Show GUI requested.")
            self._bridge.show_gui_requested.emit()
        except Exception as e:
            print(f"⚠️ Error in showGUI_ handler: {e}")

    def screenAsleep_(self, notification):
        try:
            print("\n💤 [OS EVENT] Display Sleep Detected.")
            self._waiting_for_touch = False
            self._bridge.abort_requested.emit()
            if self._system._is_macos_locked():
                print("🔒 Screen locked during sleep — pre-warming scan worker...")
                self._bridge.warm_subprocess_requested.emit()
        except Exception as e:
            print(f"⚠️ Error in screenAsleep_ handler: {e}")


class DaemonCore:

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._activity = None
        self._listener = None
        self.bridge = DaemonBridge()

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        try:
            options = NSActivityUserInitiatedAllowingIdleSystemSleep | NSActivityLatencyCritical
            self._activity = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
                options,
                "VisionSight Biometric Daemon"
            )
        except Exception as e:
            print(f"⚠️ Warning: Could not set NSProcessInfo activity: {e}")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="VisionSightDaemonThread",
            daemon=True,
        )
        self._thread.start()
        print("🚀 DaemonCore started.")

    def stop(self):
        if self._activity:
            try:
                NSProcessInfo.processInfo().endActivity_(self._activity)
            except Exception:
                pass
            self._activity = None

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        self._listener = None

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        self._listener = OSNotificationListener.alloc().initWithBridge_(self.bridge)
        listener = self._listener

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

        last_touch_check = 0.0
        try:
            while not self._stop_event.is_set():
                CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.1, False)
                time.sleep(0.1)

                if getattr(listener, "_waiting_for_touch", False):
                    now = time.time()
                    if now - last_touch_check > 0.2:
                        last_touch_check = now
                        if listener._system._is_macos_locked():
                            idle_sec = listener._system.get_seconds_since_last_input()
                            if idle_sec < 1.5:
                                listener._waiting_for_touch = False
                                print("🔒 Physical user touch detected — starting face scan...")
                                self.bridge.scan_requested.emit()
                        else:
                            listener._waiting_for_touch = False
        except Exception as e:
            print(f"⚠️ DaemonCore run-loop error: {e}")
        finally:
            try:
                dist_nc.removeObserver_(listener)
                workspace_nc.removeObserver_(listener)
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    import signal
    from PyQt6.QtWidgets import QApplication

    qt_app = QApplication(sys.argv)
    core = DaemonCore()

    core.bridge.scan_requested.connect(
        lambda: print("[STANDALONE] scan_requested")
    )
    core.bridge.abort_requested.connect(
        lambda: print("[STANDALONE] abort_requested")
    )

    core.start()

    def _handle_sigint(sig, frame):
        core.stop()
        qt_app.quit()

    signal.signal(signal.SIGINT, _handle_sigint)
    sys.exit(qt_app.exec())