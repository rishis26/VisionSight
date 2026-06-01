import os
import re
import pickle
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QSpacerItem, QSizePolicy, QListWidget, QSlider, QComboBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, 
                             QMessageBox, QFrame)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor
from gui.widgets import apply_shadow, SolidFrame, ToggleButton, StyledButton

class DashboardPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)

        header = QLabel("SYSTEM OVERVIEW")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        layout.addWidget(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(30)
        
        # Card 1: System Status
        self.status_card = self.controller.card_frame("#FFFFFF")
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
        self.daemon_toggle.toggled.connect(self.controller.toggle_daemon)
        sc_layout.addWidget(self.daemon_toggle)
        
        # Card 2: Last Auth
        self.auth_card = self.controller.card_frame("#FFFFFF")
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
        self.preview_card = self.controller.card_frame("#000000")
        pc_layout = QVBoxLayout(self.preview_card)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        
        self.dash_video = QLabel()
        self.dash_video.setMinimumHeight(300)
        self.dash_video.setStyleSheet("background-color: #000000;")
        self.dash_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pc_layout.addWidget(self.dash_video)
        
        layout.addWidget(self.preview_card, 1)


class IdentitiesPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header = QLabel("IDENTITIES")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        layout.addWidget(header)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(30)

        left_pane = self.controller.card_frame("#FFFFFF")
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

        # Live face-detection status badge
        self.face_status_label = QLabel("👁  CAMERA STARTING...")
        self.face_status_label.setFont(QFont(".AppleSystemUIFont", 12, QFont.Weight.Bold))
        self.face_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.face_status_label.setFixedHeight(36)
        self.face_status_label.setStyleSheet("""
            QLabel {
                background-color: #333333;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 4px 14px;
                letter-spacing: 1px;
            }
        """)
        left_layout.addWidget(self.face_status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
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
        btn_add.clicked.connect(self.controller.register_face)
        left_layout.addWidget(btn_add)
        
        btn_reregister = StyledButton("UPDATE ID", primary=False)
        btn_reregister.clicked.connect(self.controller.reregister_face)
        left_layout.addWidget(btn_reregister)
        left_layout.addStretch()

        right_pane = self.controller.card_frame("#FFFFFF")
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
        btn_del.clicked.connect(self.controller.delete_selected_identity)
        right_layout.addWidget(btn_del)

        split_layout.addWidget(left_pane)
        split_layout.addWidget(right_pane)
        layout.addLayout(split_layout)
        
        self.identity_list.itemSelectionChanged.connect(self.controller.show_identity_preview)
        self.name_input.textChanged.connect(lambda: self.identity_list.clearSelection())


class SettingsPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
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
        btn_apply.clicked.connect(self.controller.save_preferences)
        header_layout.addWidget(btn_apply)
        layout.addLayout(header_layout)
        
        card = self.controller.card_frame("#FFFFFF")
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
            
            form_layout.addWidget(self.controller.create_setting_row(k, v[0], w))
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
        
        form_layout.addWidget(self.controller.create_setting_row("TOLERANCE", "SECURITY STRICTNESS", sw))
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
        form_layout.addWidget(self.controller.create_setting_row("PROCESSING FPS", "FRAME RATE", self.combo_fps))

        self.combo_res = QComboBox()
        self.combo_res.addItems(["640x480", "1280x720"])
        self.combo_res.setStyleSheet(combo_style)
        self.combo_res.setCurrentIndex(0 if os.getenv("VISIONSIGHT_RESOLUTION", "640x480") == "640x480" else 1)
        form_layout.addWidget(self.controller.create_setting_row("RESOLUTION", "CAPTURE DEFINITION", self.combo_res))

        self.auto_unlock_toggle = ToggleButton(checked=os.getenv("VISIONSIGHT_AUTO_UNLOCK", "true").lower() == "true")
        form_layout.addWidget(self.controller.create_setting_row("AUTO UNLOCK", "INJECT PASSWORD", self.auto_unlock_toggle))

        form_layout.addStretch()
        layout.addWidget(card)


class SecurityPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(30)
        
        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM SECURITY")
        header.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        card = self.controller.card_frame("#FFFFFF")
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
        btn_keychain.clicked.connect(self.controller.update_keychain_password)
        form_layout.addWidget(btn_keychain)

        form_layout.addStretch()
        layout.addWidget(card)


class LogsPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
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
        self.log_filter.currentTextChanged.connect(self.controller.refresh_logs)
        header_layout.addWidget(self.log_filter)
        
        btn_clear = StyledButton("FLUSH", is_danger=True)
        btn_clear.clicked.connect(self.controller.clear_logs)
        header_layout.addWidget(btn_clear)
        
        layout.addLayout(header_layout)

        card = self.controller.card_frame("#FFFFFF")
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


class OnboardingPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.wizard_stack = QStackedWidget()
        
        # S0: PERMISSIONS
        w0 = self.controller.card_frame("#FFFFFF")
        w0_l = QVBoxLayout(w0)
        w0_l.setContentsMargins(50, 50, 50, 50)
        w0_l.setSpacing(25)
        
        t0 = QLabel("SYSTEM PERMISSIONS")
        t0.setFont(QFont(".AppleSystemUIFont", 40, QFont.Weight.Black))
        t0.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w0_l.addWidget(t0)
        
        d0 = QLabel("VisionSight runs entirely locally. We require access to your Camera to verify your identity, and Accessibility to simulate typing your login password.")
        d0.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        d0.setStyleSheet("color: #4B5563; line-height: 1.4;")
        d0.setWordWrap(True)
        d0.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w0_l.addWidget(d0)
        
        # Camera status row
        cam_row = QHBoxLayout()
        self.lbl_cam_status = QLabel("📷 CAMERA PERMISSION: CHECKING...")
        self.lbl_cam_status.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        self.lbl_cam_status.setStyleSheet("color: #000000;")
        self.btn_grant_cam = StyledButton("GRANT CAMERA", primary=False)
        self.btn_grant_cam.clicked.connect(self.request_camera_access)
        cam_row.addWidget(self.lbl_cam_status)
        cam_row.addStretch()
        cam_row.addWidget(self.btn_grant_cam)
        w0_l.addLayout(cam_row)
        
        # Accessibility status row
        acc_row = QHBoxLayout()
        self.lbl_acc_status = QLabel("♿ ACCESSIBILITY PERMISSION: CHECKING...")
        self.lbl_acc_status.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        self.lbl_acc_status.setStyleSheet("color: #000000;")
        self.btn_grant_acc = StyledButton("GRANT ACCESS", primary=False)
        self.btn_grant_acc.clicked.connect(self.open_accessibility_settings)
        acc_row.addWidget(self.lbl_acc_status)
        acc_row.addStretch()
        acc_row.addWidget(self.btn_grant_acc)
        w0_l.addLayout(acc_row)
        
        # Next Button
        self.btn_verify_perms = StyledButton("VERIFY && CONTINUE", primary=True)
        self.btn_verify_perms.setMinimumHeight(60)
        self.btn_verify_perms.clicked.connect(self.verify_permissions_and_continue)
        w0_l.addWidget(self.btn_verify_perms)
        w0_l.addStretch()
        
        # S1: PASSWORD
        w1 = self.controller.card_frame("#FFFFFF")
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
        w2 = self.controller.card_frame("#FFFFFF")
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

        # Live face-detection status badge for onboarding
        self.wiz_face_status_label = QLabel("👁  CAMERA STARTING...")
        self.wiz_face_status_label.setFont(QFont(".AppleSystemUIFont", 12, QFont.Weight.Bold))
        self.wiz_face_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wiz_face_status_label.setFixedHeight(36)
        self.wiz_face_status_label.setStyleSheet("""
            QLabel {
                background-color: #333333;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 4px 14px;
                letter-spacing: 1px;
            }
        """)
        wiz_status_row = QHBoxLayout()
        wiz_status_row.addStretch()
        wiz_status_row.addWidget(self.wiz_face_status_label)
        wiz_status_row.addStretch()
        w2_l.addLayout(wiz_status_row)
        
        self.wiz_name = QLineEdit()
        self.wiz_name.setPlaceholderText("ENTER YOUR NAME (e.g. USERNAME)")
        self.wiz_name.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Black))
        self.wiz_name.setStyleSheet("QLineEdit { padding: 16px; border: 4px solid #000000; background: #FFFFFF; color: #000000; } QLineEdit:focus { background: #00E5FF; color: #000000; }")
        w2_l.addWidget(self.wiz_name)
        
        btn_next2 = StyledButton("CAPTURE IDENTITY AND FINISH", primary=True)
        btn_next2.setMinimumHeight(60)
        btn_next2.clicked.connect(self.wizard_save_face)
        w2_l.addWidget(btn_next2)
        
        self.wizard_stack.addWidget(w0)
        self.wizard_stack.addWidget(w1)
        self.wizard_stack.addWidget(w2)
        layout.addWidget(self.wizard_stack)

    def request_camera_access(self):
        self.controller.request_camera_access()

    def open_accessibility_settings(self):
        self.controller.open_accessibility_settings()

    def refresh_permissions_status(self):
        return self.controller.refresh_permissions_status()

    def verify_permissions_and_continue(self):
        self.controller.verify_permissions_and_continue()

    def wizard_save_password(self):
        self.controller.wizard_save_password()

    def wizard_save_face(self):
        self.controller.wizard_save_face()
