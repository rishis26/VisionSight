import sys
import os
import subprocess
import cv2
import pickle
import numpy as np
import face_recognition

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QStackedWidget, 
                             QLineEdit, QFrame, QMessageBox, QSpacerItem, QSizePolicy,
                             QListWidget, QSlider, QComboBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont
from dotenv import load_dotenv, set_key

class StyledButton(QPushButton):
    def __init__(self, text, color="#0A84FF", is_danger=False):
        super().__init__(text)
        if is_danger:
            color = "#ff3b30"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._darken(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken(color, 40)};
            }}
        """)

    def _darken(self, hex_color, amount=20):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(max(0, int(hex_color[i:i+2], 16) - amount) for i in (0, 2, 4))
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


class VisionSightGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionSight Dashboard")
        self.setFixedSize(850, 550)
        self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

        # Internal state
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.encodings_path = os.path.join(self.project_dir, "assets", "known_faces", "encodings.pkl")
        self.env_path = os.path.join(self.project_dir, ".env")
        
        # Load environment vars if they exist
        if not os.path.exists(self.env_path):
            open(self.env_path, 'w').close()
        load_dotenv(self.env_path)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.camera_index = int(os.getenv("VISIONSIGHT_CAMERA", 0))

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Base Layout: Left Sidebar + Right Content Area
        self.sidebar = self.create_sidebar()
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #121212;")

        # Create Pages
        self.page_status = self.create_status_page()
        self.page_biometric = self.create_biometric_page()
        self.page_security = self.create_security_page()
        self.page_settings = self.create_settings_page()

        self.content_stack.addWidget(self.page_status)
        self.content_stack.addWidget(self.page_biometric)
        self.content_stack.addWidget(self.page_security)
        self.content_stack.addWidget(self.page_settings)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack)

        self.setCentralWidget(main_widget)
        self.switch_to_page(0)

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #2c2c2e; border-right: 1px solid #3a3a3c;")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 30, 15, 30)

        # Title
        title = QLabel("VisionSight")
        title.setFont(QFont("San Francisco", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: white; border: none; margin-bottom: 25px;")
        layout.addWidget(title)

        # Navigation Buttons
        self.btn_nav_status = self.nav_button("🔌 Daemon Status", 0)
        self.btn_nav_bio = self.nav_button("👤 Manage Identities", 1)
        self.btn_nav_sec = self.nav_button("🔐 Keychain Bindings", 2)
        self.btn_nav_set = self.nav_button("⚙️ Preferences", 3)

        layout.addWidget(self.btn_nav_status)
        layout.addWidget(self.btn_nav_bio)
        layout.addWidget(self.btn_nav_sec)
        layout.addWidget(self.btn_nav_set)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return sidebar

    def nav_button(self, text, index):
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left; padding: 12px; border-radius: 6px; 
                background: transparent; color: #a1a1a6; font-size: 14px; font-weight: 500;
                border: none; margin-bottom: 5px;
            }
            QPushButton:hover { background: #3a3a3c; color: white; }
        """)
        btn.clicked.connect(lambda: self.switch_to_page(index))
        return btn

    def switch_to_page(self, index):
        self.content_stack.setCurrentIndex(index)
        if index == 1:
            self.refresh_identity_list()
            self.start_camera()
        else:
            self.stop_camera()
            
        if index == 0:
            self.refresh_daemon_status()


    # ----------------------------------------------------
    # PAGE 1: STATUS
    # ----------------------------------------------------
    def create_status_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("System Status")
        title.setFont(QFont("San Francisco", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        self.status_label = QLabel("Checking status...")
        self.status_label.setFont(QFont("San Francisco", 16))
        self.status_label.setStyleSheet("color: #ff3b30; margin-top: 10px; margin-bottom: 30px;")
        layout.addWidget(self.status_label)

        h_layout = QHBoxLayout()
        btn_start = StyledButton("Start Engine", "#34c759")
        btn_start.clicked.connect(self.start_daemon)
        btn_stop = StyledButton("Stop Engine", is_danger=True)
        btn_stop.clicked.connect(self.stop_daemon)
        
        h_layout.addWidget(btn_start)
        h_layout.addWidget(btn_stop)
        h_layout.addStretch()
        
        layout.addLayout(h_layout)
        layout.addStretch()
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

    def refresh_daemon_status(self):
        if self.is_daemon_running():
            self.status_label.setText("🟢 VisionSight is Active Backend Service")
            self.status_label.setStyleSheet("color: #34c759; margin-top: 10px; margin-bottom: 30px;")
        else:
            self.status_label.setText("🔴 VisionSight is Offline")
            self.status_label.setStyleSheet("color: #ff3b30; margin-top: 10px; margin-bottom: 30px;")

    def start_daemon(self):
        script_path = os.path.join(self.project_dir, 'manage_daemon.sh')
        subprocess.run([script_path, 'start'], cwd=self.project_dir)
        self.refresh_daemon_status()

    def stop_daemon(self):
        script_path = os.path.join(self.project_dir, 'manage_daemon.sh')
        subprocess.run([script_path, 'stop'], cwd=self.project_dir)
        self.refresh_daemon_status()


    # ----------------------------------------------------
    # PAGE 2: BIOMETRICS (ADD / REMOVE IDENTITIES)
    # ----------------------------------------------------
    def create_biometric_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Identity Sandbox")
        title.setFont(QFont("San Francisco", 28, QFont.Weight.Bold))
        main_layout.addWidget(title)

        split_layout = QHBoxLayout()

        # Left side: Camera / Add Face
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setFixedSize(320, 240)
        self.video_label.setStyleSheet("background-color: black; border-radius: 8px;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.video_label)

        h_input = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter subject name...")
        self.name_input.setStyleSheet("padding: 8px; border-radius: 4px; background: #2c2c2e; border: 1px solid #3a3a3c;")
        
        btn_capture = StyledButton("Register")
        btn_capture.clicked.connect(self.register_face)

        h_input.addWidget(self.name_input)
        h_input.addWidget(btn_capture)
        left_layout.addLayout(h_input)
        left_layout.addStretch()

        # Right side: Saved Faces List
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 0, 0, 0)

        list_title = QLabel("Stored Identities")
        list_title.setFont(QFont("San Francisco", 14, QFont.Weight.Bold))
        right_layout.addWidget(list_title)

        self.identity_list = QListWidget()
        self.identity_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3c;
                border-radius: 6px;
                padding: 5px;
                font-size: 16px;
            }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #2c2c2e; }
            QListWidget::item:selected { background-color: #0A84FF; border-radius: 4px; color: white; }
        """)
        right_layout.addWidget(self.identity_list)

        btn_delete = StyledButton("Delete Selected", is_danger=True)
        btn_delete.clicked.connect(self.delete_selected_identity)
        right_layout.addWidget(btn_delete)
        right_layout.addStretch()

        split_layout.addWidget(left_widget)
        split_layout.addWidget(right_widget)

        main_layout.addLayout(split_layout)
        return page

    def load_encodings(self):
        if os.path.exists(self.encodings_path):
            with open(self.encodings_path, "rb") as f:
                return pickle.load(f)
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

    def delete_selected_identity(self):
        selected_items = self.identity_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Delete Error", "Please select an identity to delete.")
            return

        name = selected_items[0].text()
        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to permanently delete {name}'s biometric data?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            data = self.load_encodings()
            if name in data:
                del data[name]
                self.save_encodings(data)
                self.refresh_identity_list()
                QMessageBox.information(self, "Deleted", f"Successfully removed {name}.")

    def start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.timer.start(30)

    def stop_camera(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.video_label.clear()

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                self.current_cv_frame = frame
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pm = QPixmap.fromImage(qt_img).scaled(320, 240, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
                self.video_label.setPixmap(pm)

    def register_face(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a name first.")
            return

        if not hasattr(self, 'current_cv_frame'):
            QMessageBox.warning(self, "Error", "Camera not active or frame missing.")
            return

        btn = self.sender()
        btn.setText("Scanning...")
        btn.setEnabled(False)
        self.repaint() # Force UI update before heavy CV operation

        frame = self.current_cv_frame
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # We don't shrink the frame for registration to get maximum features extracted
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        btn.setText("Register")
        btn.setEnabled(True)

        if not face_locations:
            QMessageBox.warning(self, "Scan Failed", "No face detected in the frame. Please look directly at the camera.")
            return
            
        if len(face_locations) > 1:
            QMessageBox.warning(self, "Scan Failed", "Multiple faces detected. Please ensure only you are in the frame.")
            return

        encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if encodings:
            encoding = encodings[0]
            data = self.load_encodings()
            data[name] = encoding
            self.save_encodings(data)
                
            self.refresh_identity_list()
            QMessageBox.information(self, "Success", f"Face scanned and protected mathematically for '{name}'!")
            self.name_input.clear()


    # ----------------------------------------------------
    # PAGE 3: SECURITY (KEYCHAIN)
    # ----------------------------------------------------
    def create_security_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Hardware Keychain")
        title.setFont(QFont("San Francisco", 28, QFont.Weight.Bold))
        layout.addWidget(title)
        
        desc = QLabel("To seamlessly auto-inject your password during login, VisionSight encrypts\n"
                      "your credentials directly into the secure Apple Keychain chip.\n\n"
                      "This prevents any plaintext exposure on your disk.")
        desc.setStyleSheet("color: #a1a1a6; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(desc)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter System Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet("padding: 12px; border-radius: 6px; background: #2c2c2e; border: 1px solid #3a3a3c; font-size: 16px;")
        layout.addWidget(self.pass_input)

        btn_save = StyledButton("Authorize Mac Payload")
        btn_save.clicked.connect(self.save_to_keychain)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()
        return page

    def save_to_keychain(self):
        mac_password = self.pass_input.text()
        if not mac_password:
            QMessageBox.warning(self, "Error", "Password cannot be empty.")
            return
            
        try:
            subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], 
                           capture_output=True)
            subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', mac_password], 
                           check=True)
            QMessageBox.information(self, "Secured", "Target password successfully cryptographically sealed!")
            self.pass_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Keychain Error", f"Apple API rejected request: {e}")


    # ----------------------------------------------------
    # PAGE 4: PREFERENCES
    # ----------------------------------------------------
    def create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Engine Preferences")
        title.setFont(QFont("San Francisco", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        # Tolerance Slider Area
        tol_title = QLabel("Biometric Strictness (Tolerance)")
        tol_title.setFont(QFont("San Francisco", 16, QFont.Weight.Bold))
        tol_title.setStyleSheet("margin-top: 15px;")
        layout.addWidget(tol_title)

        tol_desc = QLabel("Lower values = High Strictness. Higher values = Faster but less precise.")
        tol_desc.setStyleSheet("color: #a1a1a6;")
        layout.addWidget(tol_desc)

        self.slider_tol = QSlider(Qt.Orientation.Horizontal)
        self.slider_tol.setMinimum(30) # 0.30
        self.slider_tol.setMaximum(60) # 0.60
        
        current_tol = float(os.getenv("VISIONSIGHT_TOLERANCE", 0.45))
        self.slider_tol.setValue(int(current_tol * 100))
        self.slider_tol.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_tol.setTickInterval(5)

        self.label_tol_val = QLabel(f"Current: {current_tol}")
        
        self.slider_tol.valueChanged.connect(self.on_tol_change)

        tol_layout = QHBoxLayout()
        tol_layout.addWidget(self.slider_tol)
        tol_layout.addWidget(self.label_tol_val)
        layout.addLayout(tol_layout)

        # Camera Index Area
        cam_title = QLabel("Camera Input Source")
        cam_title.setFont(QFont("San Francisco", 16, QFont.Weight.Bold))
        cam_title.setStyleSheet("margin-top: 25px;")
        layout.addWidget(cam_title)

        self.combo_cam = QComboBox()
        self.combo_cam.addItems(["Camera 0 (Default / Internal)", "Camera 1 (External)", "Camera 2"])
        self.combo_cam.setCurrentIndex(min(int(os.getenv("VISIONSIGHT_CAMERA", 0)), 2))
        self.combo_cam.setStyleSheet("padding: 8px; background: #2c2c2e; border: 1px solid #3a3a3c; border-radius: 4px;")
        layout.addWidget(self.combo_cam)

        layout.addSpacing(40)
        btn_apply = StyledButton("Apply & Save Preferences")
        btn_apply.clicked.connect(self.save_preferences)
        layout.addWidget(btn_apply, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()
        return page

    def on_tol_change(self, val):
        self.label_tol_val.setText(f"Current: {val / 100.0}")

    def save_preferences(self):
        new_tol = str(self.slider_tol.value() / 100.0)
        new_cam = str(self.combo_cam.currentIndex())
        
        set_key(self.env_path, "VISIONSIGHT_TOLERANCE", new_tol)
        set_key(self.env_path, "VISIONSIGHT_CAMERA", new_cam)
        
        # update live GUI var
        self.camera_index = int(new_cam)

        QMessageBox.information(self, "Saved", "Preferences successfully committed to Engine core.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("San Francisco", 12))
    
    window = VisionSightGUI()
    window.show()
    sys.exit(app.exec())
