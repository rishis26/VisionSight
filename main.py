import time
import threading
import objc
from Foundation import NSDistributedNotificationCenter, NSObject
from AppKit import NSWorkspace, NSWorkspaceScreensDidSleepNotification, NSWorkspaceScreensDidWakeNotification
from PyObjCTools import AppHelper
from system.lock import SystemController
from face_auth.verify import FaceVerifier

class OSNotificationListener(NSObject):
    def init(self):
        self = objc.super(OSNotificationListener, self).init()
        if self:
            self.system = SystemController()
            self.verifier = FaceVerifier(headless=True)
            self.scan_in_progress = False
        return self

    def screenLocked_(self, notification):
        print("\n🔒 [OS EVENT] True Hardware Lock Detected. Waiting for display wake to scan...")
        # Intentionally NOT starting scan here. 
        # Scan triggers on `screenAwake_` when you open the lid or wake the display.
        # self._start_scan_if_needed()

    def screenAwake_(self, notification):
        print("\n☀️ [OS EVENT] Display Wake Detected.")
        # If the display woke up and the Mac is still locked, we need to restart the camera!
        if self.system._is_macos_locked():
            print("🔒 System is still locked! Resuming camera scan...")
            self._start_scan_if_needed()

    def _start_scan_if_needed(self):
        if self.scan_in_progress:
            return
            
        self.scan_in_progress = True
        self.verifier._stop_requested = False
        
        scan_thread = threading.Thread(target=self._run_scan, daemon=True)
        scan_thread.start()

    def _run_scan(self):
        result = self.verifier.authenticate_once(self.system)
        
        if result == "success":
            print("✅ Scanner unlocked the system successfully.")
        elif result in ("rejected", "aborted"):
            print("🛑 Scanner operation cancelled manually.")
            
        self.scan_in_progress = False

    def screenUnlocked_(self, notification):
        print("\n🔓 [OS EVENT] True Hardware Unlock Detected.")
        if self.scan_in_progress:
            print("🛑 Aborting active camera scan...")
            self.verifier._stop_requested = True

    def screenAsleep_(self, notification):
        print("\n💤 [OS EVENT] Display Sleep Detected (You pressed Esc!).")
        if self.scan_in_progress:
            print("🛑 Aborting active camera scan immediately...")
            self.verifier._stop_requested = True

def start_daemon():
    print("==================================================")
    print("🚀 VISIONSIGHT OS SECURITY DAEMON (EVENT-DRIVEN)")
    print("==================================================")
    
    listener = OSNotificationListener.new()
    
    # 1. Distributed Notification Center (For Lock & Unlock Events)
    dist_nc = NSDistributedNotificationCenter.defaultCenter()
    dist_nc.addObserver_selector_name_object_(listener, 'screenLocked:', 'com.apple.screenIsLocked', None)
    dist_nc.addObserver_selector_name_object_(listener, 'screenUnlocked:', 'com.apple.screenIsUnlocked', None)
    
    # 2. Workspace Notification Center (For Physical Display Sleep & Wake Events)
    workspace_nc = NSWorkspace.sharedWorkspace().notificationCenter()
    workspace_nc.addObserver_selector_name_object_(listener, 'screenAsleep:', NSWorkspaceScreensDidSleepNotification, None)
    workspace_nc.addObserver_selector_name_object_(listener, 'screenAwake:', NSWorkspaceScreensDidWakeNotification, None)

    print("✅ System Ready. Listening at 0% CPU for OS Broadcasts...")
    
    try:
        # This acts as your new while True loop, but consumes exactly 0 CPU.
        AppHelper.runEventLoop()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down VisionSight Daemon.")

if __name__ == "__main__":
    start_daemon()