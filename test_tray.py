#!/usr/bin/env python3
"""
Quick test to verify system tray icon functionality.
Run this to test if the tray icon appears in your menu bar.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

class TrayTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tray Icon Test")
        self.setGeometry(100, 100, 400, 200)
        
        # Setup tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Try to use VisionSight icon
        icon_path = "assets/icon.png"
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
            print(f"✅ Using icon from: {icon_path}")
        else:
            # Use system icon as fallback
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
            print("⚠️ Using system fallback icon")
        
        # Create menu
        menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
        print("✅ Tray icon should now be visible in your menu bar!")
        print("   Look for a computer icon in the top-right corner")
        
    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
    
    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
        print("✅ Window shown")
    
    def closeEvent(self, event):
        print("🔴 Window hidden (not closed)")
        self.hide()
        self.tray_icon.showMessage(
            "Tray Test",
            "App is running in background. Click tray icon to reopen.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        event.ignore()
    
    def quit_app(self):
        print("🛑 Quitting app")
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = TrayTest()
    window.show()
    
    print("\n" + "="*60)
    print("TRAY ICON TEST")
    print("="*60)
    print("1. Look for an icon in your menu bar (top-right)")
    print("2. Close this window - it should hide, not quit")
    print("3. Click the tray icon to show the window again")
    print("4. Right-click tray icon → Quit to exit")
    print("="*60 + "\n")
    
    sys.exit(app.exec())
