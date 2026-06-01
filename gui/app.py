import sys
import os
import time
import subprocess
import pickle
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QLineEdit, QFrame, QMessageBox, QSpacerItem, QSizePolicy,
                             QStyle, QSystemTrayIcon, QMenu, QTableWidgetItem)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QIcon, QAction, QKeySequence, QShortcut
from dotenv import load_dotenv, set_key

from main import DaemonCore
from gui.widgets import apply_neumorphic_shadow, LiquidFrame, LiquidInput, ToggleButton, StyledButton, NavButton
from gui.threads import CameraThread, DaemonScanThread
from gui.pages import (DashboardPage, IdentitiesPage, SettingsPage, 
                       SecurityPage, LogsPage, OnboardingPage)

class VisionSightGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionSight - Neo Control Panel")
        self.setMinimumSize(1100, 720)

        import system.paths as paths
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.encodings_path = paths.get_encodings_path()
        self.env_path = paths.get_env_path()
        self.log_path = paths.get_log_path()
        self.icon_path = paths.get_icon_path()
        self.faces_dir = paths.get_known_faces_dir()
        
        if not os.path.exists(self.env_path):
            open(self.env_path, 'w').close()
        load_dotenv(self.env_path)

        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.camera_thread = None
        self.current_cv_frame = None
        self.identity_preview_mode = False
        self._face_detect_counter = 0   # throttle live face-detection checks

        self._daemon_core: DaemonCore | None = None
        self._scan_thread: DaemonScanThread | None = None
        self._last_scan_end: float = 0.0

        # Keyboard Shortcuts for standard macOS behaviors (Cmd+M to minimize, Cmd+Ctrl+F to fullscreen)
        self.shortcut_minimize = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_minimize.activated.connect(self.showMinimized)

        self.shortcut_fullscreen = QShortcut(QKeySequence("Ctrl+Meta+F"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)

        self.init_ui()
        self.init_tray()
        
        if self.is_onboarding_needed():
            self.sidebar.hide()
            self.content_stack.setCurrentIndex(5)
            cam_ok = self.check_camera_permission()
            acc_ok = self.check_accessibility_permission()
            if not (cam_ok and acc_ok):
                self.wizard_stack.setCurrentIndex(0)
                self.refresh_permissions_status()
            else:
                pw_exists = False
                try:
                    subprocess.check_output(['security', 'find-generic-password', '-s', 'VisionSightDaemon', '-w'], stderr=subprocess.DEVNULL)
                    pw_exists = True
                except:
                    pass
                if not pw_exists:
                    self.wizard_stack.setCurrentIndex(1)
                else:
                    self.wizard_stack.setCurrentIndex(2)
                    self.start_camera()
        else:
            QTimer.singleShot(100, lambda: self.switch_to_page(0))
            QTimer.singleShot(800, self.start_daemon_thread)

    def init_ui(self):
        main_widget = QFrame()
        main_widget.setStyleSheet("background-color: #E0E5EC;") # Liquid Morphism Base
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = self.create_sidebar()
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: transparent;")

        # Instantiate modular pages
        self.page_dashboard = DashboardPage(self)
        self.page_users = IdentitiesPage(self)
        self.page_settings = SettingsPage(self)
        self.page_security = SecurityPage(self)
        self.page_logs = LogsPage(self)
        self.page_onboarding = OnboardingPage(self)

        # Shortcut references to page widgets for direct controller access
        self.wizard_stack = self.page_onboarding.wizard_stack
        self.wiz_pass = self.page_onboarding.wiz_pass
        self.wiz_video = self.page_onboarding.wiz_video
        self.wiz_name = self.page_onboarding.wiz_name
        self.lbl_cam_status = self.page_onboarding.lbl_cam_status
        self.btn_grant_cam = self.page_onboarding.btn_grant_cam
        self.lbl_acc_status = self.page_onboarding.lbl_acc_status
        self.btn_grant_acc = self.page_onboarding.btn_grant_acc
        
        self.status_val = self.page_dashboard.status_val
        self.daemon_toggle = self.page_dashboard.daemon_toggle
        self.auth_result = self.page_dashboard.auth_result
        self.auth_time = self.page_dashboard.auth_time
        self.dash_video = self.page_dashboard.dash_video
        
        self.video_label = self.page_users.video_label
        self.name_input = self.page_users.name_input
        self.identity_list = self.page_users.identity_list
        self.face_status_label = self.page_users.face_status_label

        self.wiz_face_status_label = self.page_onboarding.wiz_face_status_label
        
        self.slider_widgets = self.page_settings.slider_widgets
        self.combo_fps = self.page_settings.combo_fps
        self.combo_res = self.page_settings.combo_res
        self.auto_unlock_toggle = self.page_settings.auto_unlock_toggle
        
        self.password_input = self.page_security.password_input
        
        self.log_filter = self.page_logs.log_filter
        self.log_table = self.page_logs.log_table

        self.content_stack.addWidget(self.page_dashboard)
        self.content_stack.addWidget(self.page_users)
        self.content_stack.addWidget(self.page_settings)
        self.content_stack.addWidget(self.page_security)
        self.content_stack.addWidget(self.page_logs)
        self.content_stack.addWidget(self.page_onboarding)

        main_layout.addWidget(self.sidebar)
        
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.addWidget(self.content_stack)
        
        main_layout.addWidget(content_container, 1)

        self.setCentralWidget(main_widget)
        
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.silent_refresh_dashboard)
        self.status_timer.start(2000)

    def silent_refresh_dashboard(self):
        if self.content_stack.currentIndex() == 0:
            self.refresh_dashboard_status()

    def check_accessibility_permission(self) -> bool:
        try:
            import ctypes
            app_services = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
            return bool(app_services.AXIsProcessTrusted())
        except Exception as e:
            print(f"⚠️ Error checking accessibility permission: {e}")
            return False

    def check_camera_permission(self) -> bool:
        try:
            import AVFoundation
            auth_status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                AVFoundation.AVMediaTypeVideo
            )
            return auth_status == 3
        except Exception as e:
            print(f"⚠️ Error checking camera permission: {e}")
            try:
                import cv2
                cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
                if cap.isOpened():
                    ret, _ = cap.read()
                    cap.release()
                    return ret
            except Exception:
                pass
            return False

    def request_camera_access(self):
        try:
            import AVFoundation
            auth_status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                AVFoundation.AVMediaTypeVideo
            )
            if auth_status == 0:
                AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                    AVFoundation.AVMediaTypeVideo,
                    lambda granted: QTimer.singleShot(100, self.refresh_permissions_status)
                )
            else:
                subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"])
        except Exception as e:
            print(f"Camera request failed: {e}")
            try:
                import cv2
                cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
                if cap.isOpened():
                    cap.release()
            except Exception:
                pass
        QTimer.singleShot(1000, self.refresh_permissions_status)

    def open_accessibility_settings(self):
        subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        QTimer.singleShot(1000, self.refresh_permissions_status)

    def refresh_permissions_status(self):
        cam_ok = self.check_camera_permission()
        acc_ok = self.check_accessibility_permission()
        
        if cam_ok:
            self.lbl_cam_status.setText("📷 CAMERA: GRANTED")
            self.lbl_cam_status.setStyleSheet("color: #000000; background: #00FF00; padding: 5px; font-weight: 900;")
            self.btn_grant_cam.setEnabled(False)
            self.btn_grant_cam.setText("AUTHORIZED")
        else:
            self.lbl_cam_status.setText("📷 CAMERA: DENIED")
            self.lbl_cam_status.setStyleSheet("color: #FFFFFF; background: #FF5555; padding: 5px; font-weight: 900;")
            self.btn_grant_cam.setEnabled(True)
            self.btn_grant_cam.setText("GRANT CAMERA")
            
        if acc_ok:
            self.lbl_acc_status.setText("♿ ACCESSIBILITY: GRANTED")
            self.lbl_acc_status.setStyleSheet("color: #000000; background: #00FF00; padding: 5px; font-weight: 900;")
            self.btn_grant_acc.setEnabled(False)
            self.btn_grant_acc.setText("AUTHORIZED")
        else:
            self.lbl_acc_status.setText("♿ ACCESSIBILITY: DENIED")
            self.lbl_acc_status.setStyleSheet("color: #FFFFFF; background: #FF5555; padding: 5px; font-weight: 900;")
            self.btn_grant_acc.setEnabled(True)
            self.btn_grant_acc.setText("GRANT ACCESS")

        return cam_ok, acc_ok

    def verify_permissions_and_continue(self):
        cam_ok, acc_ok = self.refresh_permissions_status()
        if cam_ok and acc_ok:
            self.wizard_stack.setCurrentIndex(1)
        else:
            missing = []
            if not cam_ok: missing.append("Camera")
            if not acc_ok: missing.append("Accessibility")
            QMessageBox.warning(
                self, "PERMISSIONS REQUIRED",
                "Please enable the following permissions to continue:\n" + "\n".join(f"- {m}" for m in missing)
            )

    def is_onboarding_needed(self):
        if not self.check_camera_permission() or not self.check_accessibility_permission():
            return True

        pw_exists = False
        try:
            subprocess.check_output(['security', 'find-generic-password', '-s', 'VisionSightDaemon', '-w'], stderr=subprocess.DEVNULL)
            pw_exists = True
        except:
            pass
            
        faces_exist = False
        if os.path.exists(self.encodings_path):
            try:
                with open(self.encodings_path, 'rb') as f:
                    data = pickle.load(f)
                    if len(data) > 0:
                        faces_exist = True
            except Exception as e:
                print(f"⚠️ Error loading encodings pickle: {e}")
                    
        return not (pw_exists and faces_exist)

    def wizard_save_password(self):
        pw = self.wiz_pass.text()
        if not pw:
            QMessageBox.warning(self, "ERROR", "PASSWORD REQUIRED.")
            return
        try:
            subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], capture_output=True)
            subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', pw], check=True)
            self.wizard_stack.setCurrentIndex(2)
            self.start_camera()
        except Exception as e:
            QMessageBox.warning(self, "ERROR", f"FAILED TO UPDATE KEYCHAIN: {e}")

    def wizard_save_face(self):
        if self.current_cv_frame is None: return
        name = self.wiz_name.text().strip()
        if not name:
            QMessageBox.warning(self, "ERROR", "NAME REQUIRED.")
            return
            
        import cv2
        import face_recognition

        frame = self.current_cv_frame.copy()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locs = face_recognition.face_locations(rgb_frame)
        if not locs:
            QMessageBox.warning(self, "ERROR", "NO FACE DETECTED.")
            return
        encs = face_recognition.face_encodings(rgb_frame, locs)
        if encs:
            data = self.load_encodings()
            data[name] = encs[0]
            self.save_encodings(data)
            
            img_path = os.path.join(self.faces_dir, f"{name}.jpg")
            cv2.imwrite(img_path, frame)
            
            QMessageBox.information(self, "SUCCESS", "BIOMETRIC PROFILE SECURED.")
            self.sidebar.show()
            self.switch_to_page(0)
        else:
            QMessageBox.warning(self, "ERROR", "FAILED TO ENCODE FACE.")

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            .QFrame {
                background-color: #E0E5EC;
                border-right: 2px solid #FFFFFF;
            }
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(25, 40, 25, 40)

        title_layout = QHBoxLayout()
        if os.path.exists(self.icon_path):
            logo = QLabel()
            pixmap = QPixmap(self.icon_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
            title_layout.addWidget(logo)
        else:
            logo = QLabel()
            logo_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            logo.setPixmap(logo_icon.pixmap(48, 48))
            title_layout.addWidget(logo)
            
        title_text_layout = QVBoxLayout()
        title = QLabel("VisionSight")
        title.setFont(QFont(".AppleSystemUIFont", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #000000; letter-spacing: -0.5px;")
        
        title_text_layout.addWidget(title)
        title_text_layout.setSpacing(0)
        
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        layout.addSpacing(60)

        self.nav_btns = [
            NavButton("OVERVIEW", 0, self.switch_to_page, QStyle.StandardPixmap.SP_ComputerIcon),
            NavButton("IDENTITIES", 1, self.switch_to_page, QStyle.StandardPixmap.SP_DirIcon),
            NavButton("CONFIG", 2, self.switch_to_page, QStyle.StandardPixmap.SP_FileDialogDetailedView),
            NavButton("SYSTEM SEC", 3, self.switch_to_page, QStyle.StandardPixmap.SP_DriveHDIcon),
            NavButton("LOG FILES", 4, self.switch_to_page, QStyle.StandardPixmap.SP_FileIcon)
        ]
        
        for btn in self.nav_btns:
            layout.addWidget(btn)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        btn_quit = QPushButton("Quit VisionSight")
        btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quit.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Medium))
        btn_quit.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 10px 16px;
                background: #FFFFFF;
                color: #FF3B30;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                margin-bottom: 10px;
            }
            QPushButton:hover { background: #FF3B30; color: #FFFFFF; border: none; }
            QPushButton:pressed { opacity: 0.8; }
        """)
        btn_quit.clicked.connect(self.quit_app)
        apply_neumorphic_shadow(btn_quit, 10, 2)
        layout.addWidget(btn_quit)

        footer = QLabel("Version 5.0 • Main Terminal")
        footer.setFont(QFont(".AppleSystemUIFont", 11, QFont.Weight.Medium))
        footer.setStyleSheet("color: #8E8E93; padding: 10px; background: transparent;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        credit = QLabel('A project by <a href="https://github.com/rishis26" style="color:#007AFF; text-decoration:none;">Rishi Shah</a>')
        credit.setFont(QFont(".AppleSystemUIFont", 11, QFont.Weight.Medium))
        credit.setStyleSheet("QLabel { color: #8E8E93; padding: 4px; text-align: center; }")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setOpenExternalLinks(True)
        credit.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(credit)

        return sidebar

    def card_frame(self, bg_color="#E0E5EC"):
        return LiquidFrame(radius=24)

    def switch_to_page(self, index):
        for i, btn in enumerate(self.nav_btns):
            btn.set_active(i == index)
            
        self.content_stack.setCurrentIndex(index)
        
        if index == 0:
            self.refresh_dashboard_status()
            if self.isVisible():
                self.start_camera()
        elif index == 1:
            self.refresh_identity_list()
            if self.isVisible():
                self.start_camera() 
        elif index == 4:
            self.stop_camera()
            self.refresh_logs()
        else:
            self.stop_camera()

    def is_daemon_running(self) -> bool:
        return self._daemon_core is not None and self._daemon_core.is_alive()

    def start_daemon_thread(self):
        if self.is_daemon_running():
            return
        self._daemon_core = DaemonCore()
        self._daemon_core.bridge.scan_requested.connect(self._on_daemon_scan_requested)
        self._daemon_core.bridge.abort_requested.connect(self._on_daemon_abort_requested)
        self._daemon_core.bridge.show_gui_requested.connect(self.show_and_raise)
        self._daemon_core.start()

    def stop_daemon_thread(self):
        self._on_daemon_abort_requested()
        if self._daemon_core:
            self._daemon_core.stop()
            self._daemon_core = None

    def toggle_daemon(self, state):
        if state:
            self.start_daemon_thread()
        else:
            self.stop_daemon_thread()
        QTimer.singleShot(600, self.refresh_dashboard_status)

    def _on_daemon_scan_requested(self):
        if self._scan_thread and self._scan_thread.isRunning():
            return

        import system.paths as paths
        from dotenv import load_dotenv
        load_dotenv(paths.get_env_path(), override=True)
        cooldown = int(os.getenv("VISIONSIGHT_COOLDOWN", "10"))
        elapsed = time.time() - self._last_scan_end
        if elapsed < cooldown:
            return

        self.stop_camera()
        self._scan_thread = DaemonScanThread(parent=self)
        self._scan_thread.scan_complete.connect(self._on_daemon_scan_complete)
        self._scan_thread.start()

    def _on_daemon_abort_requested(self):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.abort()

    def _on_daemon_scan_complete(self, result: str, user_name: str):
        self._last_scan_end = time.time()
        self._scan_thread = None

        if result == "success" and user_name:
            from system.lock import SystemController
            main_thread_controller = SystemController()
            main_thread_controller.simulate_unlock(user_name)

        if self.isVisible() and self.content_stack.currentIndex() in [0, 1]:
            self.start_camera()


    def refresh_dashboard_status(self):
        running = self.is_daemon_running()
        if not running:
            self.status_val.setText("OFFLINE")
            self.status_val.setStyleSheet("color: #FFFFFF; background: #FF5555; padding: 0 5px;")
            self.daemon_toggle.setCheckedNoSignal(False)
        else:
            self.daemon_toggle.setCheckedNoSignal(True)
            state = "IDLE"
            style = "color: #000000; background: #FFD500; padding: 0 5px;"
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r') as f:
                    lines = f.readlines()
                last_meaningful = ""
                for line in reversed(lines):
                    if line.strip():
                        last_meaningful = line
                        break

                if "Lock Detected" in last_meaningful or "System is still locked" in last_meaningful:
                    state = "LOCKED"
                    style = "color: #FFFFFF; background: #FF5555; padding: 0 5px;"
                elif "SCANNING" in last_meaningful or "Resuming camera scan" in last_meaningful:
                    state = "ACTIVE"
                    style = "color: #000000; background: #00F0FF; padding: 0 5px;"
                elif "Aborting" in last_meaningful or "cancelled" in last_meaningful or "cooldown" in last_meaningful.lower():
                    state = "COOLDOWN"
                    style = "color: #000000; background: #B026FF; padding: 0 5px;"

            self.status_val.setText(state)
            self.status_val.setStyleSheet(style)

            if state in ["ACTIVE", "LOCKED"]:
                self.stop_camera()
            elif state in ["IDLE", "COOLDOWN"]:
                if self.isVisible() and self.content_stack.currentIndex() in [0, 1]:
                    self.start_camera()
        
        self.update_tray_daemon_status()

        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                content = f.read()
            if "Identity Verified" in content and "Verification Failed" in content:
                last_fail = content.rfind("Verification Failed")
                last_succ = content.rfind("Identity Verified")
                if last_succ > last_fail:
                    self.auth_result.setText("VERIFIED")
                    self.auth_result.setStyleSheet("color: #000000; background: #FFD500; padding: 0 5px;")
                else:
                    self.auth_result.setText("REJECTED")
                    self.auth_result.setStyleSheet("color: #FFFFFF; background: #FF5555; padding: 0 5px;")
            elif "Identity Verified" in content:
                self.auth_result.setText("VERIFIED")
                self.auth_result.setStyleSheet("color: #000000; background: #FFD500; padding: 0 5px;")
            elif "Verification Failed" in content:
                self.auth_result.setText("REJECTED")
                self.auth_result.setStyleSheet("color: #FFFFFF; background: #FF5555; padding: 0 5px;")
            else:
                self.auth_result.setText("NO DATA")
                self.auth_result.setStyleSheet("color: #000000; background: transparent;")
                self.auth_time.setText("--")
                return

            mod_time = os.path.getmtime(self.log_path)
            import datetime
            dt = datetime.datetime.fromtimestamp(mod_time)
            self.auth_time.setText("TRIGGERED: " + dt.strftime("%B %d, %I:%M %p").upper())

    def show_identity_preview(self):
        selected = self.identity_list.selectedItems()
        if not selected:
            self.identity_preview_mode = False
            return
            
        name = selected[0].text()
        img_path = os.path.join(self.faces_dir, f"{name}.jpg")
        self.identity_preview_mode = True
        
        if os.path.exists(img_path):
            self.video_label.setStyleSheet("")
            pixmap = QPixmap(img_path).scaled(360, 270, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
        else:
            self.video_label.clear()
            self.video_label.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: 900;")
            self.video_label.setText("NO PREVIEW FOUND")

    def load_encodings(self):
        if os.path.exists(self.encodings_path):
            try:
                with open(self.encodings_path, "rb") as f:
                    return pickle.load(f)
            except:
                pass
        return {}

    def save_encodings(self, data):
        os.makedirs(os.path.dirname(self.encodings_path), exist_ok=True)
        with open(self.encodings_path, "wb") as f:
            pickle.dump(data, f)

    def refresh_identity_list(self):
        self.identity_list.clear()
        data = self.load_encodings()
        for name in data.keys():
            self.identity_list.addItem(name)

    def register_face(self, is_reregister=False, target_name=None):
        name = target_name or self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "ERROR", "ENTER A NAME FIRST.")
            return

        if self.current_cv_frame is None:
            QMessageBox.warning(self, "ERROR", "CAMERA OFFLINE.")
            return

        import cv2
        import face_recognition

        btn = self.sender()
        original_text = btn.text()
        btn.setText("SCANNING...")
        btn.setEnabled(False)
        QApplication.processEvents()

        frame = self.current_cv_frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        btn.setText(original_text)
        btn.setEnabled(True)

        if not face_locations:
            QMessageBox.warning(self, "FAILED", "NO FACE DETECTED.")
            return
        if len(face_locations) > 1:
            QMessageBox.warning(self, "FAILED", "MULTIPLE FACES DETECTED.")
            return

        encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if encodings:
            encoding = encodings[0]
            data = self.load_encodings()
            data[name] = encoding
            self.save_encodings(data)
            
            img_path = os.path.join(self.faces_dir, f"{name}.jpg")
            cv2.imwrite(img_path, frame)
            
            self.refresh_identity_list()
            QMessageBox.information(self, "SUCCESS", f"REGISTERED: {name}")
            if not is_reregister:
                self.name_input.clear()

    def reregister_face(self):
        selected = self.identity_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "ERROR", "SELECT USER.")
            return
        name = selected[0].text()
        self.register_face(is_reregister=True, target_name=name)

    def delete_selected_identity(self):
        selected_items = self.identity_list.selectedItems()
        if not selected_items: return

        name = selected_items[0].text()
        data = self.load_encodings()
        if name in data:
            del data[name]
            self.save_encodings(data)
            
            img_path = os.path.join(self.faces_dir, f"{name}.jpg")
            if os.path.exists(img_path):
                os.remove(img_path)
                
            self.identity_list.clearSelection()
            self.refresh_identity_list()

    def start_camera(self):
        if self.camera_thread is not None and self.camera_thread.isRunning():
            return
            
        camera_idx_env = os.getenv("VISIONSIGHT_CAMERA", "0")
        camera_idx = int(camera_idx_env) if camera_idx_env.isdigit() else 0
            
        self.camera_thread = CameraThread(camera_idx)
        self.camera_thread.new_frame.connect(self.update_frame)
        self.camera_thread.start()

    def stop_camera(self):
        if self.camera_thread is not None and self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.camera_thread = None
            
        self.dash_video.clear()
        self.video_label.clear()
        self.current_cv_frame = None

    def _update_face_status_badge(self, raw_frame, badge_label):
        """Run a quick HOG face-detect on the current frame and update the badge.
        Called at most every 10 frames (~300 ms) to keep the UI smooth."""
        import cv2
        import face_recognition

        try:
            small = cv2.resize(raw_frame, (0, 0), fx=0.5, fy=0.5)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, model="hog")
        except Exception:
            locs = []

        if not locs:
            badge_label.setText("\u274c  NO FACE DETECTED")
            badge_label.setStyleSheet("""
                QLabel {
                    background-color: #D32F2F;
                    color: #FFFFFF;
                    border-radius: 8px;
                    padding: 4px 14px;
                    letter-spacing: 1px;
                }
            """)
        elif len(locs) > 1:
            badge_label.setText("\u26a0\ufe0f  MULTIPLE FACES")
            badge_label.setStyleSheet("""
                QLabel {
                    background-color: #E65100;
                    color: #FFFFFF;
                    border-radius: 8px;
                    padding: 4px 14px;
                    letter-spacing: 1px;
                }
            """)
        else:
            badge_label.setText("\u2705  FACE DETECTED \u2014 READY")
            badge_label.setStyleSheet("""
                QLabel {
                    background-color: #2E7D32;
                    color: #FFFFFF;
                    border-radius: 8px;
                    padding: 4px 14px;
                    letter-spacing: 1px;
                }
            """)

    def update_frame(self, qt_img, raw_frame):
        self.current_cv_frame = raw_frame
        self._face_detect_counter += 1
        
        if self.content_stack.currentIndex() == 0:
            pm = QPixmap.fromImage(qt_img).scaled(
                self.dash_video.width(), self.dash_video.height(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation)
            self.dash_video.setPixmap(pm)
        elif self.content_stack.currentIndex() == 1:
            if not getattr(self, "identity_preview_mode", False):
                self.video_label.setStyleSheet("")
                pm = QPixmap.fromImage(qt_img).scaled(
                    360, 270, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation)
                self.video_label.setPixmap(pm)
                # Throttled live face-detection badge (every 10 frames)
                if self._face_detect_counter % 10 == 0:
                    self._update_face_status_badge(raw_frame, self.face_status_label)
            else:
                # Preview mode: reset badge to neutral
                self.face_status_label.setText("\U0001f441  IDENTITY PREVIEW")
                self.face_status_label.setStyleSheet("""
                    QLabel {
                        background-color: #333333;
                        color: #FFFFFF;
                        border-radius: 8px;
                        padding: 4px 14px;
                        letter-spacing: 1px;
                    }
                """)
        elif getattr(self, "content_stack", None) and getattr(self.content_stack, "currentIndex", lambda: -1)() == 5:
            if hasattr(self, 'wizard_stack') and self.wizard_stack.currentIndex() == 2:
                pm = QPixmap.fromImage(qt_img).scaled(
                    360, 270, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation)
                self.wiz_video.setPixmap(pm)
                # Throttled live face-detection badge for onboarding
                if self._face_detect_counter % 10 == 0:
                    self._update_face_status_badge(raw_frame, self.wiz_face_status_label)

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        if os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            
        self.tray_menu = QMenu()
        
        self.tray_status_action = QAction("Status: Checking...", self)
        self.tray_status_action.setEnabled(False)
        self.tray_menu.addAction(self.tray_status_action)
        
        self.tray_menu.addSeparator()
        
        open_action = QAction("Open Dashboard", self)
        open_action.triggered.connect(self.show_and_raise)
        self.tray_menu.addAction(open_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings_page)
        self.tray_menu.addAction(settings_action)
        
        self.tray_menu.addSeparator()
        
        self.start_action = QAction("Start Protection", self)
        self.start_action.triggered.connect(self.start_daemon_thread)
        self.tray_menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Protection", self)
        self.stop_action.triggered.connect(self.stop_daemon_thread)
        self.tray_menu.addAction(self.stop_action)
        
        self.tray_menu.addSeparator()

        self.logs_menu = QMenu("Recent Logs", self)
        self.tray_menu.addMenu(self.logs_menu)
        self.refresh_tray_logs_submenu()
        
        self.tray_menu.addSeparator()
        
        quit_action = QAction("Quit VisionSight", self)
        quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        self.tray_icon.show()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def set_mac_activation_policy_regular(self):
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyRegular
            ns_app = NSApplication.sharedApplication()
            ns_app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            ns_app.activateIgnoringOtherApps_(True)
        except Exception as e:
            print(f"⚠️ Could not set activation policy to Regular: {e}")

    def set_mac_activation_policy_accessory(self):
        try:
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            ns_app = NSApplication.sharedApplication()
            ns_app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print(f"⚠️ Could not set activation policy to Accessory: {e}")

    def show_and_raise(self):
        print("🖥️ [GUI EVENT] Raising dashboard GUI window to front...")
        self.set_mac_activation_policy_regular()
        self.show()
        self.activateWindow()
        self.raise_()
        self.switch_to_page(0)

    def open_settings_page(self):
        self.set_mac_activation_policy_regular()
        self.show()
        self.activateWindow()
        self.raise_()
        self.switch_to_page(2)

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            if self.isVisible():
                self.hide()
                self.stop_camera()
            else:
                self.show_and_raise()

    def refresh_tray_logs_submenu(self):
        self.logs_menu.clear()
        if not os.path.exists(self.log_path):
            self.logs_menu.addAction("No log file found.").setEnabled(False)
            return
            
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            recent = []
            for line in reversed(lines):
                line = line.strip()
                if line:
                    clean_line = re.sub(r'[\U00010000-\U0010ffff]', '', line).strip()
                    for rep in ["✅", "❌", "🛑", "⚠️", "🔒", "🟢", "👁️", "💤", "☀️", "🔄", "🔓"]:
                        clean_line = clean_line.replace(rep, "")
                    clean_line = clean_line.strip()
                    if clean_line:
                        recent.append(clean_line)
                        if len(recent) >= 5:
                            break
            
            if not recent:
                self.logs_menu.addAction("No recent events.").setEnabled(False)
            else:
                for log in recent:
                    action = QAction(log, self)
                    action.setEnabled(False)
                    self.logs_menu.addAction(action)
        except Exception as e:
            self.logs_menu.addAction(f"Error reading logs: {str(e)}").setEnabled(False)

    def update_tray_daemon_status(self):
        if not hasattr(self, 'tray_icon') or not self.tray_icon.isVisible():
            return
            
        running = self.is_daemon_running()
        if not running:
            self.tray_status_action.setText("Status: OFFLINE")
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
        else:
            state = "IDLE"
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r') as f:
                    lines = f.readlines()
                last_meaningful = ""
                for line in reversed(lines):
                    if line.strip():
                        last_meaningful = line
                        break
                
                if "Lock Detected" in last_meaningful or "System is still locked" in last_meaningful:
                    state = "LOCKED"
                elif "SCANNING" in last_meaningful or "Resuming camera scan" in last_meaningful:
                    state = "ACTIVE"
                elif "Aborting" in last_meaningful or "cancelled" in last_meaningful or "cooldown" in last_meaningful.lower():
                    state = "COOLDOWN"
            
            self.tray_status_action.setText(f"Status: {state}")
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            
        self.refresh_tray_logs_submenu()

    def closeEvent(self, event):
        if not hasattr(self, 'tray_icon') or not self.tray_icon.isVisible():
            print("⚠️ No system tray - performing normal quit")
            self.quit_app()
            return
        
        print("🔴 Window closing — hiding to system tray...")
        self.stop_camera()
        import cv2
        cv2.destroyAllWindows()
        self.hide()
        self.set_mac_activation_policy_accessory()
        
        if not hasattr(self, '_first_hide_done'):
            self.tray_icon.showMessage(
                "VisionSight",
                "App is running in the background. Click the tray icon to open.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            self._first_hide_done = True
        event.ignore()
    
    def installQuitFilter(self, qapp):
        self._qapp = qapp
        qapp.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self._qapp and event.type() == QEvent.Type.Quit:
            if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
                self.closeEvent(type('FakeCloseEvent', (), {'ignore': lambda s: None, 'accept': lambda s: None})())
                return True
        return super().eventFilter(obj, event)

    def quit_app(self):
        print("🛑 Shutting down VisionSight completely...")
        try:
            if hasattr(self, 'status_timer') and self.status_timer.isActive():
                self.status_timer.stop()

            if hasattr(self, '_scan_thread') and self._scan_thread and self._scan_thread.isRunning():
                self._scan_thread.abort()
                self._scan_thread.wait(800)

            self.stop_camera()
            import cv2
            cv2.destroyAllWindows()

            if hasattr(self, '_daemon_core') and self._daemon_core:
                self._daemon_core.stop()
                self._daemon_core = None

            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()

            print("✅ VisionSight terminated.")
        except Exception as e:
            print(f"⚠️ quit_app cleanup error (ignored): {e}")
        finally:
            os._exit(0)

    def create_setting_row(self, title, desc, widget):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 10, 0, 10)
        
        text_layout = QVBoxLayout()
        t = QLabel(title)
        t.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        t.setStyleSheet("color: #000000;")
        
        d = QLabel(desc)
        d.setFont(QFont(".AppleSystemUIFont", 12, QFont.Weight.Bold))
        d.setStyleSheet("color: #4B5563;")
        
        text_layout.addWidget(t)
        text_layout.addWidget(d)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(widget)
        return row

    def save_preferences(self):
        for name, data in self.page_settings.sliders.items():
            set_key(self.env_path, data[5], str(self.slider_widgets[name].value()))
            
        strictness = str(self.slider_widgets["TOLERANCE"].value() / 100.0)
        set_key(self.env_path, "VISIONSIGHT_TOLERANCE", strictness)
            
        fps_text = self.combo_fps.currentText()
        fps_val = "Low" if "Low" in fps_text else "High" if "High" in fps_text else "Medium"
        set_key(self.env_path, "VISIONSIGHT_FPS", fps_val)
        
        set_key(self.env_path, "VISIONSIGHT_RESOLUTION", self.combo_res.currentText())
        set_key(self.env_path, "VISIONSIGHT_AUTO_UNLOCK", "true" if self.auto_unlock_toggle.isChecked() else "false")

    def update_keychain_password(self):
        mac_password = self.password_input.text()
        if not mac_password:
            QMessageBox.warning(self, "ERROR", "PASSWORD CANNOT BE EMPTY.")
            return
            
        try:
            subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], capture_output=True)
            subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', mac_password], check=True)
            QMessageBox.information(self, "SUCCESS", "PASSWORD SECURELY ENCRYPTED IN KEYCHAIN.")
            self.password_input.clear()
        except Exception as e:
            QMessageBox.warning(self, "ERROR", f"FAILED TO UPDATE KEYCHAIN: {e}")

    def refresh_logs(self):
        self.log_table.setRowCount(0)
        if not os.path.exists(self.log_path):
            return
            
        with open(self.log_path, 'r') as f:
            lines = f.readlines()
            
        filter_type = self.log_filter.currentText()
        
        parsed_logs = []
        for line in reversed(lines):
            line = line.strip()
            if not line: continue
            
            if "Verified" in line or "Granted" in line or "✅" in line:
                status = "SUCCESS"
            elif "❌" in line or "🛑" in line or "⚠️" in line or "Denied" in line or "Failed" in line:
                status = "DENIED"
            elif "🔒" in line or "🟢" in line or "👁️" in line or "Event" in line:
                status = "SYSTEM"
            else:
                continue
                
            if filter_type == "SUCCESS" and status != "SUCCESS": continue
            if filter_type == "DENIED" and status != "DENIED": continue
                
            clean_str = re.sub(r'[\U00010000-\U0010ffff]', '', line)
            clean_str = clean_str.replace("✅", "").replace("❌", "").replace("🛑", "").replace("⚠️", "").replace("🔒", "").replace("🟢", "").replace("👁️", "").strip()
                
            parsed_logs.append(("RECENT", status, clean_str))
            if len(parsed_logs) >= 50: break
                
        self.log_table.setRowCount(len(parsed_logs))
        for row, log in enumerate(parsed_logs):
            self.log_table.setItem(row, 0, QTableWidgetItem(log[0]))
            
            status_item = QTableWidgetItem(log[1])
            status_item.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Black))
            if log[1] == "SUCCESS":
                status_item.setBackground(QColor("#FFD500"))
            elif log[1] == "DENIED":
                status_item.setBackground(QColor("#FF5555"))
                status_item.setForeground(QColor("#FFFFFF"))
            else:
                status_item.setBackground(QColor("#E2E8F0"))
                
            self.log_table.setItem(row, 1, status_item)
            self.log_table.setItem(row, 2, QTableWidgetItem(log[2]))

    # ── Reset / Uninstall ─────────────────────────────────────────────────────

    def _wipe_app_data(self) -> list[str]:
        """Remove all VisionSight user data. Returns a list of result messages."""
        import shutil
        msgs = []

        # 1. Stop daemon & camera cleanly
        self.stop_daemon_thread()
        self.stop_camera()

        # 2. Remove keychain entry
        try:
            subprocess.run(
                ['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'],
                capture_output=True
            )
            msgs.append("✅ Keychain entry deleted.")
        except Exception as e:
            msgs.append(f"⚠️ Keychain: {e}")

        # 3. Wipe Application Support directory
        import system.paths as paths
        app_data = paths.get_app_data_dir()
        if os.path.exists(app_data):
            try:
                shutil.rmtree(app_data)
                msgs.append(f"✅ App data removed: {app_data}")
            except Exception as e:
                msgs.append(f"⚠️ App data: {e}")
        else:
            msgs.append("ℹ️ No app data directory found.")

        return msgs

    def reset_all_data(self):
        """Erase all user data and return to onboarding, keeping the CLI installed."""
        reply = QMessageBox.warning(
            self,
            "⚠  RESET ALL DATA",
            "This will permanently delete:\n\n"
            "  • All registered biometric profiles\n"
            "  • All audit logs\n"
            "  • Your saved Mac password (keychain)\n"
            "  • All configuration settings\n\n"
            "VisionSight will restart into the initial setup wizard.\n\n"
            "This action CANNOT be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        msgs = self._wipe_app_data()
        summary = "\n".join(msgs)
        QMessageBox.information(self, "RESET COMPLETE", f"All data erased.\n\n{summary}\n\nRestarting setup wizard...")

        # Restart the GUI process so onboarding triggers cleanly
        import sys
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def uninstall_app(self):
        """Erase all data, remove the global CLI symlink + shell alias, then quit."""
        reply = QMessageBox.warning(
            self,
            "⚠  UNINSTALL VISIONSIGHT",
            "This will COMPLETELY remove VisionSight:\n\n"
            "  • All registered biometric profiles\n"
            "  • All audit logs\n"
            "  • Your saved Mac password (keychain)\n"
            "  • All configuration settings\n"
            "  • Global 'visionsight' CLI command (/usr/local/bin)\n"
            "  • The 'vs' shell alias from ~/.zshrc\n\n"
            "The application will quit after uninstalling.\n\n"
            "This action CANNOT be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        msgs = self._wipe_app_data()

        # Remove global CLI symlink
        cli_path = "/usr/local/bin/visionsight"
        if os.path.exists(cli_path) or os.path.islink(cli_path):
            try:
                os.remove(cli_path)
                msgs.append("✅ CLI symlink removed: /usr/local/bin/visionsight")
            except PermissionError:
                result = subprocess.run(["sudo", "rm", "-f", cli_path], capture_output=True)
                if result.returncode == 0:
                    msgs.append("✅ CLI symlink removed (via sudo).")
                else:
                    msgs.append("⚠️ Could not remove CLI symlink — run: sudo rm /usr/local/bin/visionsight")
            except Exception as e:
                msgs.append(f"⚠️ CLI symlink: {e}")
        else:
            msgs.append("ℹ️ No global CLI symlink found.")

        # Remove alias from ~/.zshrc
        zshrc_path = os.path.expanduser("~/.zshrc")
        alias_marker = "# VisionSight — short alias (added by visionsight install)"
        alias_line = 'alias vs="visionsight"'
        if os.path.exists(zshrc_path):
            try:
                with open(zshrc_path, "r") as f:
                    content = f.read()
                # Remove marker comment + alias line block
                cleaned = content.replace(f"\n{alias_marker}\n{alias_line}\n", "")
                # Fallback: remove just the alias line in case it was added without the comment
                cleaned = cleaned.replace(f"\n{alias_line}\n", "\n")
                if cleaned != content:
                    with open(zshrc_path, "w") as f:
                        f.write(cleaned)
                    msgs.append("✅ Shell alias removed from ~/.zshrc")
                else:
                    msgs.append("ℹ️ No 'vs' alias found in ~/.zshrc")
            except Exception as e:
                msgs.append(f"⚠️ ~/.zshrc: {e}")

        summary = "\n".join(msgs)
        QMessageBox.information(
            self, "UNINSTALL COMPLETE",
            f"VisionSight has been uninstalled.\n\n{summary}\n\nThe application will now quit."
        )
        self.quit_app()

    def clear_logs(self):
        reply = QMessageBox.question(self, "FLUSH SYSTEM", "ERASE ALL AUDIT LOGS?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            open(self.log_path, 'w').close()
            self.refresh_logs()

if __name__ == "__main__":
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        ns_app = NSApplication.sharedApplication()
        ns_app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        print("✅ NSApplication policy set to Accessory (Hidden from Dock)")
    except Exception as e:
        print(f"⚠️ Could not set activation policy: {e}")

    import system.paths as _log_paths
    _log_file_path = _log_paths.get_log_path()
    os.makedirs(os.path.dirname(_log_file_path), exist_ok=True)

    if getattr(sys, 'frozen', False):
        _log_file = open(_log_file_path, 'a', buffering=1)
        sys.stdout = _log_file
        sys.stderr = _log_file
        print("=" * 50)
        print("VisionSight bundled app started")
        print("=" * 50)

        try:
            import AVFoundation
            auth_status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
                AVFoundation.AVMediaTypeVideo
            )
            print(f"📷 [FROZEN] Camera auth status: {auth_status}")
            if auth_status == 0:
                print("📷 [FROZEN] Requesting camera permission via AVFoundation...")
                AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                    AVFoundation.AVMediaTypeVideo,
                    lambda granted: print(f"📷 Camera permission {'granted' if granted else 'denied'}")
                )
            elif auth_status == 3:
                print("📷 [FROZEN] Camera already authorized")
            else:
                print(f"⚠️ [FROZEN] Camera not authorized (status={auth_status})")
        except Exception as e:
            print(f"⚠️ [FROZEN] AVFoundation probe failed: {e}")

        print(f"📂 [FROZEN] _MEIPASS = {sys._MEIPASS}")
    else:
        # Tee stdout/stderr to both terminal and daemon.log in development/CLI mode
        class TeeLogger:
            def __init__(self, filepath, stream):
                self.stream = stream
                self.log = open(filepath, 'a', buffering=1)
            def write(self, message):
                self.stream.write(message)
                self.log.write(message)
            def flush(self):
                self.stream.flush()
                self.log.flush()
        
        sys.stdout = TeeLogger(_log_file_path, sys.stdout)
        sys.stderr = TeeLogger(_log_file_path, sys.stderr)
        print("=" * 50)
        print("VisionSight dev app started (Tee logging active)")
        print("=" * 50)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    import system.paths as _paths
    _icon_path = _paths.get_icon_path()
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
        print(f"✅ QApplication icon set from: {_icon_path}")
    else:
        print(f"⚠️ Icon not found at: {_icon_path}")

    window = VisionSightGUI()
    window.installQuitFilter(app)
    
    if ("--tray" in sys.argv or "--minimized" in sys.argv) and not window.is_onboarding_needed():
        print("📥 Starting minimized in the system tray...")
        window.stop_camera()
        window.set_mac_activation_policy_accessory()
    else:
        window.set_mac_activation_policy_regular()
        window.show()
        
    app.exec()
    os._exit(0)
