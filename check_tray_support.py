#!/usr/bin/env python3
"""
Check if QSystemTrayIcon is supported on this macOS system.
"""

import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QT_VERSION_STR
from PyQt6 import QtCore

print("="*60)
print("SYSTEM TRAY SUPPORT CHECK")
print("="*60)

app = QApplication(sys.argv)

print(f"Qt Version: {QT_VERSION_STR}")
print(f"PyQt6 Version: {QtCore.PYQT_VERSION_STR}")
print(f"Platform: {sys.platform}")

# Check if system tray is available
if QSystemTrayIcon.isSystemTrayAvailable():
    print("\n✅ System Tray IS AVAILABLE")
    print("   QSystemTrayIcon should work on this system.")
else:
    print("\n❌ System Tray NOT AVAILABLE")
    print("   QSystemTrayIcon will not work on this system.")
    print("\n   Possible reasons:")
    print("   - macOS version too old")
    print("   - Running in a headless environment")
    print("   - System tray disabled in macOS settings")

# Check if system tray is supported
if QSystemTrayIcon.supportsMessages():
    print("\n✅ System Tray Messages ARE SUPPORTED")
    print("   Notifications will work.")
else:
    print("\n⚠️ System Tray Messages NOT SUPPORTED")
    print("   Notifications may not work.")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)

if QSystemTrayIcon.isSystemTrayAvailable():
    print("Your system supports system tray icons.")
    print("The VisionSight tray icon should work.")
    print("\nIf you don't see the icon:")
    print("1. Check if it's hidden in the menu bar overflow (>>)")
    print("2. Try restarting the app")
    print("3. Check System Settings → Control Center → Menu Bar Only")
else:
    print("Your system does NOT support system tray icons.")
    print("VisionSight will quit when you close the window.")
    print("\nAlternative: Run the daemon separately:")
    print("  python main.py")

print("="*60)

sys.exit(0)
