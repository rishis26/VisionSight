import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import cv2
import pickle
import numpy as np
import face_recognition
import re

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QLineEdit, QFrame, QMessageBox, QSpacerItem, QSizePolicy,
                             QListWidget, QSlider, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QGraphicsDropShadowEffect, QStyle)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal, QSize, pyqtProperty
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QBrush, QIcon, QPen
from dotenv import load_dotenv, set_key

# ---------------------------------------------------------
# NEO-BRUTALIST UI COMPONENTS
# ---------------------------------------------------------

def apply_shadow(widget, blur_radius=0, x_offset=6, y_offset=6, alpha=255, color="#000000"):
    # Hard offset shadows with 0 blur - the signature of Neo-Brutalism!
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(QColor(color))
    shadow.setOffset(x_offset, y_offset)
    widget.setGraphicsEffect(shadow)

class SolidFrame(QFrame):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#FAF9F6")) 

class ToggleButton(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 38)
        self._checked = checked
        self._track_color = QColor("#FFD500") if checked else QColor("#FFFFFF")
        self._thumb_pos = self.width() - 32 if checked else 6
        
        self.animation = QPropertyAnimation(self, b"thumb_pos")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(150)

    def isChecked(self):
        return self._checked

    def setCheckedNoSignal(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.start_transition()

    def start_transition(self):
        self.animation.stop()
        if self._checked:
            self.animation.setEndValue(self.width() - 32)
            self._track_color = QColor("#FFD500") # Neo yellow
        else:
            self.animation.setEndValue(6)
            self._track_color = QColor("#FFFFFF")
        self.animation.start()

    @pyqtProperty(float)
    def thumb_pos(self):
        return self._thumb_pos

    @thumb_pos.setter
    def thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setCheckedNoSignal(not self._checked)
        self.toggled.emit(self._checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track
        painter.setBrush(QBrush(self._track_color))
        painter.setPen(QPen(QColor("#000000"), 3))
        painter.drawRect(0, 0, self.width(), self.height())
        
        # Thumb
        painter.setBrush(QBrush(QColor("#000000")))
        painter.drawRect(int(self._thumb_pos), 5, 26, 28)

class CameraThread(QThread):
    new_frame = pyqtSignal(QImage, object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._run_flag = True
        self.cap = None

    def run(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while self._run_flag:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
                self.new_frame.emit(qt_img, frame)
            self.msleep(30)
            
        self.cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class StyledButton(QPushButton):
    def __init__(self, text, primary=True, is_danger=False):
        super().__init__(text)
        self.primary = primary
        self.is_danger = is_danger
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()
        apply_shadow(self, 0, 4, 4, 255, "#000000")

    def update_style(self):
        if self.is_danger:
            bg = "#FF5555" # Hard red
            text_color = "#000000"
        elif self.primary:
            bg = "#FFD500" # Hard yellow
            text_color = "#000000"
        else:
            bg = "#FFFFFF" # Hard white
            text_color = "#000000"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: 3px solid #000000;
                border-radius: 0px;
                padding: 14px 24px;
                font-size: 16px;
                font-weight: 900;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background-color: #00E5FF;
            }}
            QPushButton:pressed {{
                background-color: #000000;
                color: #FFFFFF;
            }}
        """)

class NavButton(QPushButton):
    def __init__(self, text, idx, callback, icon_enum=None):
        super().__init__(text)
        self.idx = idx
        self.callback = callback
        if icon_enum:
            self.setIcon(QApplication.style().standardIcon(icon_enum))
            self.setIconSize(QSize(20, 20))
            
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.default_style = """
            QPushButton {
                text-align: left; padding: 14px 20px;
                background: transparent; color: #000000; font-size: 16px; font-weight: 900;
                border: 3px solid transparent; margin-bottom: 12px;
            }
            QPushButton:hover { border: 3px solid #000000; background: #FFD500; }
        """
        self.active_style = """
            QPushButton {
                text-align: left; padding: 14px 20px;
                background: #00E5FF; color: #000000; font-size: 16px; font-weight: 900;
                border: 3px solid #000000; margin-bottom: 12px;
            }
        """
        self.setStyleSheet(self.default_style)
        self.clicked.connect(self.on_click)
        
    def on_click(self):
        self.callback(self.idx)
        
    def set_active(self, is_active):
        self.setStyleSheet(self.active_style if is_active else self.default_style)
        if is_active:
            apply_shadow(self, 0, 4, 4, 255, "#000000")
        else:
            self.setGraphicsEffect(None)


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

        self.init_ui()
        if self.is_onboarding_needed():
            self.sidebar.hide()
            self.content_stack.setCurrentIndex(5)
            self.start_camera()
        else:
            QTimer.singleShot(100, lambda: self.switch_to_page(0))

    def init_ui(self):
        main_widget = SolidFrame()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = self.create_sidebar()
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: transparent;")

        self.page_dashboard = self.create_dashboard_page()
        self.page_users = self.create_users_page()
        self.page_settings = self.create_settings_page()
        self.page_security = self.create_security_page()
        self.page_logs = self.create_logs_page()
        self.page_onboarding = self.create_onboarding_page()

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

    def is_onboarding_needed(self):
        pw_exists = False
        try:
            subprocess.check_output(['security', 'find-generic-password', '-s', 'VisionSightDaemon', '-w'], stderr=subprocess.DEVNULL)
            pw_exists = True
        except:
            pass
            
        faces_exist = False
        if os.path.exists(self.encodings_path):
            with open(self.encodings_path, 'rb') as f:
                data = pickle.load(f)
                if len(data) > 0:
                    faces_exist = True
                    
        return not (pw_exists and faces_exist)

    def create_onboarding_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.wizard_stack = QStackedWidget()
        
        # S1: PASSWORD
        w1 = self.card_frame("#FFFFFF")
        w1_l = QVBoxLayout(w1)
        w1_l.setContentsMargins(50, 50, 50, 50)
        w1_l.setSpacing(30)
        
        t1 = QLabel("WELCOME TO VISIONSIGHT")
        t1.setFont(QFont(".AppleSystemUIFont", 48, QFont.Weight.Black))
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w1_l.addWidget(t1)
        
        d1 = QLabel("Before you can use the frictionless biometric bypass, you need to securely inject your Mac password.\n\n🔒 PRIVACY GUARANTEE: Your password is encrypted natively into the Apple Mac hardware keychain enclave.\nIt never touches the cloud and is strictly physically localized to your machine.")
        d1.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        d1.setStyleSheet("color: #4B5563; line-height: 1.5;")
        d1.setWordWrap(True)
        d1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w1_l.addWidget(d1)
        
        self.wiz_pass = QLineEdit()
        self.wiz_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.wiz_pass.setPlaceholderText("ENTER MAC LOGIN PASSWORD TO CONTINUE...")
        self.wiz_pass.setFont(QFont(".AppleSystemUIFont", 20, QFont.Weight.Black))
        self.wiz_pass.setMinimumHeight(70)
        self.wiz_pass.setStyleSheet("QLineEdit { padding: 20px; background: #FFFFFF; border: 4px solid #000000; color: #000000; } QLineEdit:focus { background: #00E5FF; color: #000000; }")
        w1_l.addWidget(self.wiz_pass)
        
        btn_next1 = StyledButton("ENCRYPT TO KEYCHAIN && CONTINUE", primary=True)
        btn_next1.setMinimumHeight(70)
        btn_next1.clicked.connect(self.wizard_save_password)
        w1_l.addWidget(btn_next1)
        w1_l.addStretch()
        
        # S2: FACE
        w2 = self.card_frame("#FFFFFF")
        w2_l = QVBoxLayout(w2)
        w2_l.setContentsMargins(50, 50, 50, 50)
        w2_l.setSpacing(20)
        
        t2 = QLabel("BIOMETRIC REGISTRATION")
        t2.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w2_l.addWidget(t2)
        
        d2 = QLabel("Look directly at the camera. Ensure your face is clearly visible.")
        d2.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        d2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w2_l.addWidget(d2)
        
        self.wiz_video = QLabel()
        self.wiz_video.setFixedSize(360, 270)
        self.wiz_video.setStyleSheet("background-color: #000000; border: 4px solid #000000;")
        self.wiz_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        vid_row = QHBoxLayout()
        vid_row.addStretch()
        vid_row.addWidget(self.wiz_video)
        vid_row.addStretch()
        w2_l.addLayout(vid_row)
        
        self.wiz_name = QLineEdit()
        self.wiz_name.setPlaceholderText("ENTER YOUR NAME (e.g. USERNAME)")
        self.wiz_name.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        self.wiz_name.setStyleSheet("QLineEdit { padding: 16px; border: 4px solid #000000; background: #FFFFFF; color: #000000; } QLineEdit:focus { background: #00E5FF; color: #000000; }")
        w2_l.addWidget(self.wiz_name)
        
        btn_next2 = StyledButton("CAPTURE IDENTITY AND FINISH", primary=True)
        btn_next2.setMinimumHeight(60)
        btn_next2.clicked.connect(self.wizard_save_face)
        w2_l.addWidget(btn_next2)
        
        self.wizard_stack.addWidget(w1)
        self.wizard_stack.addWidget(w2)
        layout.addWidget(self.wizard_stack)
        
        return page

    def wizard_save_password(self):
        pw = self.wiz_pass.text()
        if not pw:
            QMessageBox.warning(self, "ERROR", "PASSWORD REQUIRED.")
            return
        try:
            subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], capture_output=True)
            subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', pw], check=True)
            self.wizard_stack.setCurrentIndex(1)
        except Exception as e:
            QMessageBox.warning(self, "ERROR", f"FAILED TO UPDATE KEYCHAIN: {e}")

    def wizard_save_face(self):
        if self.current_cv_frame is None: return
        name = self.wiz_name.text().strip()
        if not name:
            QMessageBox.warning(self, "ERROR", "NAME REQUIRED.")
            return
            
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
                background-color: #FFFFFF;
                border-right: 4px solid #000000;
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
        title = QLabel("VISIONSIGHT")
        title.setFont(QFont(".AppleSystemUIFont", 20, QFont.Weight.Black))
        title.setStyleSheet("color: #000000; letter-spacing: 2px;")
        
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
        
        footer = QLabel("VERSION 4.1\nMAIN TERMINAL")
        footer.setFont(QFont(".AppleSystemUIFont", 12, QFont.Weight.Black))
        footer.setStyleSheet("color: #000000; border: 3px solid #000000; padding: 10px; background: #FFD500;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        apply_shadow(footer, 0, 4, 4, 255, "#000000")
        layout.addWidget(footer)
        
        return sidebar

    def card_frame(self, bg_color="#FFFFFF"):
        card = QFrame()
        card.setStyleSheet(f"""
            .QFrame {{
                background-color: {bg_color};
                border: 4px solid #000000;
                border-radius: 0px;
            }}
        """)
        apply_shadow(card, 0, 8, 8, 255, "#000000")
        return card

    def switch_to_page(self, index):
        for i, btn in enumerate(self.nav_btns):
            btn.set_active(i == index)
            
        self.content_stack.setCurrentIndex(index)
        
        if index == 0:
            self.refresh_dashboard_status()
            self.start_camera()
        elif index == 1:
            self.refresh_identity_list()
            self.start_camera() 
        elif index == 4:
            self.stop_camera()
            self.refresh_logs()
        else:
            self.stop_camera()

    # ----------------------------------------------------
    # PAGE 1: DASHBOARD
    # ----------------------------------------------------
    def create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)

        header = QLabel("SYSTEM OVERVIEW")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        layout.addWidget(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(30)
        
        # Card 1: System Status
        self.status_card = self.card_frame("#FFFFFF")
        sc_layout = QVBoxLayout(self.status_card)
        sc_layout.setContentsMargins(30, 30, 30, 30)
        
        sc_title = QLabel("DAEMON STATE")
        sc_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Black))
        sc_title.setStyleSheet("color: #000000;")
        
        self.status_val = QLabel("CHECKING...")
        self.status_val.setFont(QFont(".AppleSystemUIFont", 36, QFont.Weight.Black))
        self.status_val.setStyleSheet("color: #000000;")
        
        sc_layout.addWidget(sc_title)
        sc_layout.addSpacing(5)
        sc_layout.addWidget(self.status_val)
        sc_layout.addStretch()
        
        self.daemon_toggle = ToggleButton(checked=False)
        self.daemon_toggle.toggled.connect(self.toggle_daemon)
        sc_layout.addWidget(self.daemon_toggle)
        
        # Card 2: Last Auth
        self.auth_card = self.card_frame("#FFFFFF")
        ac_layout = QVBoxLayout(self.auth_card)
        ac_layout.setContentsMargins(30, 30, 30, 30)
        
        ac_title = QLabel("LAST EVENT")
        ac_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Black))
        ac_title.setStyleSheet("color: #000000;")
        
        self.auth_result = QLabel("SUCCESS")
        self.auth_result.setFont(QFont(".AppleSystemUIFont", 36, QFont.Weight.Black))
        self.auth_result.setStyleSheet("color: #000000; background: #FFD500; padding: 0px 5px;")
        
        self.auth_time = QLabel("09:41 AM")
        self.auth_time.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.auth_time.setStyleSheet("color: #000000; margin-top: 10px;")
        
        ac_layout.addWidget(ac_title)
        ac_layout.addSpacing(5)
        ac_layout.addWidget(self.auth_result)
        ac_layout.addWidget(self.auth_time)
        ac_layout.addStretch()

        cards_layout.addWidget(self.status_card)
        cards_layout.addWidget(self.auth_card)
        layout.addLayout(cards_layout)

        # Video Preview
        self.preview_card = self.card_frame("#000000")
        pc_layout = QVBoxLayout(self.preview_card)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.dash_video = QLabel()
        self.dash_video.setMinimumHeight(300)
        self.dash_video.setStyleSheet("background-color: #000000;")
        self.dash_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pc_layout.addWidget(self.dash_video)
        
        layout.addWidget(self.preview_card, 1)

        return page

    def is_daemon_running(self):
        try:
            output = subprocess.check_output('launchctl list | grep com.visionsight.daemon', shell=True, text=True)
            parts = output.strip().split()
            if len(parts) > 0 and parts[0] != '-':
                return True
            return False
        except subprocess.CalledProcessError:
            return False

    def create_and_load_plist(self):
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.visionsight.daemon.plist")
        
        if getattr(sys, 'frozen', False):
            daemon_exe = os.path.join(os.path.dirname(sys.executable), "VisionSightDaemon")
        else:
            daemon_exe = sys.executable + " " + os.path.abspath(os.path.join(self.project_dir, "main.py"))

        import system.paths as paths
        app_data = paths.get_app_data_dir()
        log_file = os.path.join(app_data, 'logs', 'daemon.log')
        err_file = os.path.join(app_data, 'logs', 'daemon.err')
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.visionsight.daemon</string>
    <key>ProgramArguments</key>
    <array>
"""
        import shlex
        for arg in shlex.split(daemon_exe):
            plist_content += f"        <string>{arg}</string>\n"
            
        plist_content += f"""    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{err_file}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
        <key>PYTHONPATH</key>
        <string>{self.project_dir}</string>
    </dict>
</dict>
</plist>
"""
        with open(plist_path, "w") as f:
            f.write(plist_content)
        
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        res_load = subprocess.run(["launchctl", "load", plist_path], capture_output=True, text=True)
        res_start = subprocess.run(["launchctl", "start", "com.visionsight.daemon"], capture_output=True, text=True)
        
        if res_load.returncode != 0:
            print(f"Launchctl Load Error: {res_load.stderr}")

    def uninstall_daemon(self):
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.visionsight.daemon.plist")
        subprocess.run(["launchctl", "stop", "com.visionsight.daemon"], capture_output=True)
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        if os.path.exists(plist_path):
            os.remove(plist_path)

    def toggle_daemon(self, state):
        if state:
            # Recreate and load plist on every START operation to guarantee paths and environment are always in-sync
            self.create_and_load_plist()
        else:
            # Fully dismantle to defeat launchd's aggressive KeepAlive resurrection 
            self.uninstall_daemon()

        QTimer.singleShot(500, self.refresh_dashboard_status)

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
            
            # Coordination: Release the camera if daemon needs it, reacquire if on camera pages and daemon is free
            if state in ["ACTIVE", "LOCKED"]:
                self.stop_camera()
            elif state in ["IDLE", "COOLDOWN"]:
                if self.content_stack.currentIndex() in [0, 1]:
                    self.start_camera()
            
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

    # ----------------------------------------------------
    # PAGE 2: USERS
    # ----------------------------------------------------
    def create_users_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header = QLabel("IDENTITIES")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        layout.addWidget(header)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(30)

        left_pane = self.card_frame("#FFFFFF")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(30, 30, 30, 30)
        left_layout.setSpacing(20)
        
        vid_frame = QFrame()
        vid_frame.setFixedSize(360, 270)
        vid_frame.setStyleSheet("background-color: #000000; border: 4px solid #000000;")
        v_l = QVBoxLayout(vid_frame)
        v_l.setContentsMargins(0,0,0,0)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_l.addWidget(self.video_label)
        apply_shadow(vid_frame, 0, 6, 6, 255, "#000000")
        
        left_layout.addWidget(vid_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("IDENTITY NAME")
        self.name_input.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 16px; background: #FFFFFF; 
                border: 3px solid #000000; color: #000000; font-weight: 900;
            }
            QLineEdit:focus { background: #FFD500; }
        """)
        left_layout.addWidget(self.name_input)
        
        btn_add = StyledButton("REGISTER ID", primary=True)
        btn_add.clicked.connect(lambda: self.register_face())
        left_layout.addWidget(btn_add)
        
        btn_reregister = StyledButton("UPDATE ID", primary=False)
        btn_reregister.clicked.connect(self.reregister_face)
        left_layout.addWidget(btn_reregister)
        left_layout.addStretch()

        right_pane = self.card_frame("#FFFFFF")
        right_layout = QVBoxLayout(right_pane)
        right_layout.setContentsMargins(30, 30, 30, 30)
        right_layout.setSpacing(15)
        
        list_title = QLabel("AUTHORIZED IDS")
        list_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Black))
        list_title.setStyleSheet("color: #000000;")
        right_layout.addWidget(list_title)

        self.identity_list = QListWidget()
        self.identity_list.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.identity_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: 3px solid #000000;
                color: #000000;
                padding: 5px;
            }
            QListWidget::item { 
                padding: 15px 20px; 
                border-bottom: 2px solid #000000; 
            }
            QListWidget::item:hover {
                background-color: #E2E8F0;
            }
            QListWidget::item:selected { 
                background: #00E5FF;
                color: #000000; 
                border: 2px solid #000000;
            }
        """)
        right_layout.addWidget(self.identity_list)
        
        btn_del = StyledButton("REVOKE", is_danger=True)
        btn_del.clicked.connect(self.delete_selected_identity)
        right_layout.addWidget(btn_del)

        split_layout.addWidget(left_pane)
        split_layout.addWidget(right_pane)
        layout.addLayout(split_layout)
        
        self.identity_list.itemSelectionChanged.connect(self.show_identity_preview)
        self.name_input.textChanged.connect(lambda: self.identity_list.clearSelection())
        
        return page

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
            pixmap = QPixmap(img_path).scaled(360, 270, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
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

        btn = self.sender()
        original_text = btn.text()
        btn.setText("SCANNING...")
        btn.setEnabled(False)
        app.processEvents()

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

    def update_frame(self, qt_img, raw_frame):
        self.current_cv_frame = raw_frame
        
        if self.content_stack.currentIndex() == 0:
            pm = QPixmap.fromImage(qt_img).scaled(
                self.dash_video.width(), self.dash_video.height(), 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation)
            self.dash_video.setPixmap(pm)
        elif self.content_stack.currentIndex() == 1:
            if not getattr(self, "identity_preview_mode", False):
                self.video_label.setStyleSheet("")
                pm = QPixmap.fromImage(qt_img).scaled(
                    360, 270, 
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                    Qt.TransformationMode.SmoothTransformation)
                self.video_label.setPixmap(pm)
        elif getattr(self, "content_stack", None) and getattr(self.content_stack, "currentIndex", lambda: -1)() == 5:
            pm = QPixmap.fromImage(qt_img).scaled(
                360, 270, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation)
            self.wiz_video.setPixmap(pm)

    def closeEvent(self, event):
        if hasattr(self, 'status_timer') and self.status_timer.isActive():
            self.status_timer.stop()
            
        self.stop_camera()
        cv2.destroyAllWindows()
        event.accept()

    # ----------------------------------------------------
    # PAGE 3: SETTINGS
    # ----------------------------------------------------
    
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

    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header_layout = QHBoxLayout()
        header = QLabel("CONFIGURATION")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        btn_apply = StyledButton("SAVE SETTINGS", primary=True)
        btn_apply.setFixedWidth(200)
        btn_apply.clicked.connect(self.save_preferences)
        header_layout.addWidget(btn_apply)
        layout.addLayout(header_layout)
        
        card = self.card_frame("#FFFFFF")
        form_layout = QVBoxLayout(card)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(15)

        self.sliders = {
            "SCAN WINDOW": ("SECONDS OF ACTIVE SCAN", 2, 6, "4", 1, "VISIONSIGHT_ACTIVATION_WINDOW"),
            "COOLDOWN": ("SECONDS BEFORE NEXT TRIGGER", 5, 15, "10", 1, "VISIONSIGHT_COOLDOWN"),
            "IDLE THRESHOLD": ("SECONDS TO IDLE", 2, 10, "4", 1, "VISIONSIGHT_IDLE_THRESHOLD")
        }
        
        self.slider_widgets = {}
        for k, v in self.sliders.items():
            s = QSlider(Qt.Orientation.Horizontal)
            s.setMinimum(v[1])
            s.setMaximum(v[2])
            s.setValue(int(os.getenv(v[5], v[3])))
            s.setFixedWidth(240)
            s.setStyleSheet("""
                QSlider::groove:horizontal { border: 3px solid #000000; height: 16px; background: #FFFFFF; }
                QSlider::handle:horizontal { background: #000000; width: 30px; margin: -5px 0; }
                QSlider::sub-page:horizontal { background: #FFD500; border-right: 3px solid #000000; }
            """)
            val_label = QLabel(f"{s.value()}S")
            val_label.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
            val_label.setStyleSheet("color: #000000; min-width: 40px;")
            
            s.valueChanged.connect(lambda val, lbl=val_label: lbl.setText(f"{val}S"))
            
            w = QWidget()
            wl = QHBoxLayout(w)
            wl.setContentsMargins(0,0,0,0)
            wl.addWidget(s)
            wl.addSpacing(15)
            wl.addWidget(val_label)
            
            form_layout.addWidget(self.create_setting_row(k, v[0], w))
            self.slider_widgets[k] = s

        strict_s = QSlider(Qt.Orientation.Horizontal)
        strict_s.setMinimum(40)
        strict_s.setMaximum(70)
        strict_s.setValue(int(float(os.getenv("VISIONSIGHT_TOLERANCE", "0.55")) * 100))
        strict_s.setFixedWidth(240)
        strict_s.setStyleSheet("""
                QSlider::groove:horizontal { border: 3px solid #000000; height: 16px; background: #FFFFFF; }
                QSlider::handle:horizontal { background: #000000; width: 30px; margin: -5px 0; }
                QSlider::sub-page:horizontal { background: #00E5FF; border-right: 3px solid #000000; }
        """)
        strict_val = QLabel(f"{strict_s.value()/100.0}")
        strict_val.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        strict_val.setStyleSheet("color: #000000; min-width: 40px;")
        strict_s.valueChanged.connect(lambda val, lbl=strict_val: lbl.setText(f"{val/100.0}"))
        
        sw = QWidget()
        swl = QHBoxLayout(sw)
        swl.setContentsMargins(0,0,0,0)
        swl.addWidget(strict_s)
        swl.addSpacing(15)
        swl.addWidget(strict_val)
        
        form_layout.addWidget(self.create_setting_row("TOLERANCE", "SECURITY STRICTNESS", sw))
        self.slider_widgets["TOLERANCE"] = strict_s

        combo_style = """
            QComboBox {
                background: #FFFFFF; color: #000000; 
                border: 3px solid #000000; font-size: 16px; font-weight: 900;
                min-width: 180px;
                min-height: 46px;
                padding-left: 15px;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 3px solid #000000;
                color: #000000;
                selection-background-color: #FFD500;
                selection-color: #000000;
            }
        """
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["Low (5 FPS)", "Medium (10 FPS)", "High (15 FPS)"])
        self.combo_fps.setStyleSheet(combo_style)
        current_fps = os.getenv("VISIONSIGHT_FPS", "Medium")
        self.combo_fps.setCurrentIndex(0 if "Low" in current_fps else 2 if "High" in current_fps else 1)
        form_layout.addWidget(self.create_setting_row("PROCESSING FPS", "FRAME RATE", self.combo_fps))

        self.combo_res = QComboBox()
        self.combo_res.addItems(["640x480", "1280x720"])
        self.combo_res.setStyleSheet(combo_style)
        self.combo_res.setCurrentIndex(0 if os.getenv("VISIONSIGHT_RESOLUTION", "640x480") == "640x480" else 1)
        form_layout.addWidget(self.create_setting_row("RESOLUTION", "CAPTURE DEFINITION", self.combo_res))

        self.auto_unlock_toggle = ToggleButton(checked=os.getenv("VISIONSIGHT_AUTO_UNLOCK", "true").lower() == "true")
        form_layout.addWidget(self.create_setting_row("AUTO UNLOCK", "INJECT PASSWORD", self.auto_unlock_toggle))



        form_layout.addStretch()
        layout.addWidget(card)
        return page

    def save_preferences(self):
        for name, data in self.sliders.items():
            set_key(self.env_path, data[5], str(self.slider_widgets[name].value()))
            
        strictness = str(self.slider_widgets["TOLERANCE"].value() / 100.0)
        set_key(self.env_path, "VISIONSIGHT_TOLERANCE", strictness)
            
        fps_text = self.combo_fps.currentText()
        fps_val = "Low" if "Low" in fps_text else "High" if "High" in fps_text else "Medium"
        set_key(self.env_path, "VISIONSIGHT_FPS", fps_val)
        
        set_key(self.env_path, "VISIONSIGHT_RESOLUTION", self.combo_res.currentText())
        set_key(self.env_path, "VISIONSIGHT_AUTO_UNLOCK", "true" if self.auto_unlock_toggle.isChecked() else "false")

    def create_security_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM SECURITY")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        card = self.card_frame("#FFFFFF")
        form_layout = QVBoxLayout(card)
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.setSpacing(25)

        info = QLabel("VISIONSIGHT KEYCHAIN ACCESS")
        info.setFont(QFont(".AppleSystemUIFont", 24, QFont.Weight.Black))
        info.setStyleSheet("color: #000000;")
        form_layout.addWidget(info)
        
        desc = QLabel("Your Mac password is required to bypass the Lock Screen immediately upon facial recognition.\nThis string is natively routed and encrypted deep inside the macOS Apple Keychain hardware enclave.\nIt is strictly read-only by the Daemon and is never written to disk or transmitted.")
        desc.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        desc.setStyleSheet("color: #4B5563; line-height: 1.5;")
        desc.setWordWrap(True)
        form_layout.addWidget(desc)
        
        form_layout.addSpacing(20)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("ENTER YOUR MAC LOGIN PASSWORD...")
        self.password_input.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        self.password_input.setMinimumHeight(60)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 18px; background: #FFFFFF; 
                border: 4px solid #000000; color: #000000;
            }
            QLineEdit:focus { background: #00E5FF; border: 4px solid #000000; }
        """)
        form_layout.addWidget(self.password_input)
        
        btn_keychain = StyledButton("ENCRYPT TO APPLE KEYCHAIN", primary=True)
        btn_keychain.setMinimumHeight(60)
        btn_keychain.clicked.connect(self.update_keychain_password)
        form_layout.addWidget(btn_keychain)

        form_layout.addStretch()
        layout.addWidget(card)
        return page

    def update_keychain_password(self):
        mac_password = self.password_input.text()
        if not mac_password:
            QMessageBox.warning(self, "ERROR", "PASSWORD CANNOT BE EMPTY.")
            return
            
        try:
            import getpass
            subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], capture_output=True)
            subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', mac_password], check=True)
            QMessageBox.information(self, "SUCCESS", "PASSWORD SECURELY ENCRYPTED IN KEYCHAIN.")
            self.password_input.clear()
        except Exception as e:
            QMessageBox.warning(self, "ERROR", f"FAILED TO UPDATE KEYCHAIN: {e}")

    # ----------------------------------------------------
    # PAGE 4: LOGS
    # ----------------------------------------------------
    def create_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM AUDIT")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        self.log_filter = QComboBox()
        self.log_filter.addItems(["ALL", "SUCCESS", "DENIED"])
        self.log_filter.setStyleSheet("""
            QComboBox {
                background: #FFFFFF; color: #000000; 
                border: 3px solid #000000; font-size: 16px; font-weight: 900;
                min-width: 140px;
                min-height: 46px;
                padding-left: 15px;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 3px solid #000000;
                color: #000000;
                selection-background-color: #FFD500;
                selection-color: #000000;
            }
        """)
        self.log_filter.currentTextChanged.connect(self.refresh_logs)
        header_layout.addWidget(self.log_filter)
        
        btn_clear = StyledButton("FLUSH", is_danger=True)
        btn_clear.clicked.connect(self.clear_logs)
        header_layout.addWidget(btn_clear)
        
        layout.addLayout(header_layout)

        card = self.card_frame("#FFFFFF")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)

        self.log_table = QTableWidget(0, 3)
        self.log_table.setHorizontalHeaderLabels(["TIMEFRAME", "RESULT", "EVENT LOG"])
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.log_table.setShowGrid(False)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Bold))
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
                color: #000000;
            }
            QTableWidget::item {
                padding: 15px;
                border-bottom: 2px solid #000000;
            }
            QTableWidget::item:selected {
                background-color: #FFD500;
            }
            QHeaderView::section {
                background-color: transparent;
                padding: 15px;
                border: none;
                border-bottom: 3px solid #000000;
                font-weight: 900;
                color: #000000;
                font-size: 14px;
            }
        """)
        card_layout.addWidget(self.log_table)
        layout.addWidget(card)

        return page

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
                
            # STRIP ALL EMOJIS (Neo-Brutalism text-only requirement)
            clean_str = re.sub(r'[\U00010000-\U0010ffff]', '', line) # Strips emojis
            clean_str = clean_str.replace("✅", "").replace("❌", "").replace("🛑", "").replace("⚠️", "").replace("🔒", "").replace("🟢", "").replace("👁️", "").strip()
                
            parsed_logs.append(("RECENT", status, clean_str))
            if len(parsed_logs) >= 50: break
                
        self.log_table.setRowCount(len(parsed_logs))
        for row, log in enumerate(parsed_logs):
            self.log_table.setItem(row, 0, QTableWidgetItem(log[0]))
            
            status_item = QTableWidgetItem(log[1])
            status_item.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Black))
            if log[1] == "SUCCESS":
                status_item.setBackground(QColor("#FFD500")) # Yellow
            elif log[1] == "DENIED":
                status_item.setBackground(QColor("#FF5555")) # Pinkish Red
                status_item.setForeground(QColor("#FFFFFF"))
            else:
                status_item.setBackground(QColor("#E2E8F0"))
                
            self.log_table.setItem(row, 1, status_item)
            self.log_table.setItem(row, 2, QTableWidgetItem(log[2]))

    def clear_logs(self):
        reply = QMessageBox.question(self, "FLUSH SYSTEM", "ERASE ALL AUDIT LOGS?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            open(self.log_path, 'w').close()
            self.refresh_logs()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VisionSightGUI()
    window.show()
    app.exec()
    os._exit(0)
