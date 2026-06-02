import os
import re
import pickle
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QSpacerItem, QSizePolicy, QListWidget, QSlider, QComboBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, 
                             QMessageBox, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor
from gui.widgets import apply_apple_shadow, GlassCard, ToggleButton, StyledButton

class DashboardPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        header = QLabel("SYSTEM OVERVIEW")
        header.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(30)
        
        # Card 1: System Status
        self.status_card = self.controller.card_frame("#FFFFFF")
        sc_layout = QVBoxLayout(self.status_card)
        sc_layout.setContentsMargins(30, 30, 30, 30)
        
        sc_title = QLabel("DAEMON STATE")
        sc_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Bold))
        sc_title.setStyleSheet("color: #FFFFFF;")
        
        self.status_val = QLabel("CHECKING...")
        self.status_val.setFont(QFont(".AppleSystemUIFont", 36, QFont.Weight.Bold))
        self.status_val.setStyleSheet("color: #FFFFFF;")
        
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
        ac_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Bold))
        ac_title.setStyleSheet("color: #FFFFFF;")
        
        self.auth_result = QLabel("SUCCESS")
        self.auth_result.setFont(QFont(".AppleSystemUIFont", 36, QFont.Weight.Bold))
        self.auth_result.setStyleSheet("color: #FFFFFF; color: #0A84FF;")
        
        self.auth_time = QLabel("09:41 AM")
        self.auth_time.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.auth_time.setStyleSheet("color: #FFFFFF; margin-top: 10px;")
        
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
        self.dash_video.setStyleSheet("background-color: #FFFFFF;")
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
        layout.setSpacing(20)
        
        header = QLabel("IDENTITIES")
        header.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(header)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(30)

        left_pane = self.controller.card_frame("#FFFFFF")
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(30, 30, 30, 30)
        left_layout.setSpacing(20)
        
        vid_frame = QFrame()
        vid_frame.setFixedSize(360, 270)
        vid_frame.setStyleSheet("background-color: #FFFFFF; border: none; border-radius: 20px;")
        v_l = QVBoxLayout(vid_frame)
        v_l.setContentsMargins(0,0,0,0)
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_l.addWidget(self.video_label)
        apply_apple_shadow(vid_frame)
        
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
                border-radius: 20px;
                padding: 4px 14px;
                letter-spacing: 1px;
            }
        """)
        left_layout.addWidget(self.face_status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("IDENTITY NAME")
        self.name_input.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.name_input.setStyleSheet("""
            QLineEdit { padding: 16px 20px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: #FFFFFF; font-weight: 500; font-size: 16px; }
            QLineEdit:focus { background: rgba(255, 255, 255, 0.1); border: 1px solid #0A84FF; color: #FFFFFF; }
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
        list_title.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Bold))
        list_title.setStyleSheet("color: #FFFFFF;")
        right_layout.addWidget(list_title)

        self.identity_list = QListWidget()
        self.identity_list.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.identity_list.setStyleSheet("""
            QListWidget { background-color: transparent; border: none; color: #FFFFFF; padding: 4px; }
                QListWidget::item { padding: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
                QListWidget::item:hover { background-color: transparent; border-radius: 8px; }
                QListWidget::item:selected { background: #0A84FF; color: #FFFFFF; border-radius: 8px; }
        """)
        right_layout.addWidget(self.identity_list)
        
        btn_del = StyledButton("REVOKE", is_danger=True)
        btn_del.clicked.connect(self.controller.delete_selected_identity)
        right_layout.addWidget(btn_del)

        split_layout.addWidget(left_pane)
        split_layout.addWidget(right_pane)
        layout.addLayout(split_layout, 1)
        
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
        layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        header = QLabel("CONFIGURATION")
        header.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
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
                QSlider::groove:horizontal { border-radius: 2px; height: 4px; background: rgba(255, 255, 255, 0.2); }
                QSlider::handle:horizontal { background: #FFFFFF; width: 24px; margin: -10px 0; border-radius: 12px; border: 1px solid rgba(0,0,0,0.1); }
                QSlider::sub-page:horizontal { background: #0A84FF; border-radius: 2px; }
            """)
            val_label = QLabel(f"{s.value()}S")
            val_label.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
            val_label.setStyleSheet("color: #FFFFFF; min-width: 40px;")
            
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
                QSlider::groove:horizontal { border-radius: 2px; height: 4px; background: rgba(255, 255, 255, 0.2); }
                QSlider::handle:horizontal { background: #FFFFFF; width: 24px; margin: -10px 0; border-radius: 12px; border: 1px solid rgba(0,0,0,0.1); }
                QSlider::sub-page:horizontal { background: #0A84FF; border-radius: 2px; }
        """)
        strict_val = QLabel(f"{strict_s.value()/100.0}")
        strict_val.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        strict_val.setStyleSheet("color: #FFFFFF; min-width: 40px;")
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
                padding: 10px 16px;
                background: rgba(255, 255, 255, 0.05); color: #FFFFFF; 
                border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; font-size: 14px; font-weight: 600;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #FFFFFF;
                selection-background-color: #0A84FF;
                outline: none;
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
        layout.addWidget(card, 1)


class SecurityPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM SECURITY")
        header.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # ── Outer card (border + shadow) ──────────────────────────────────────
        card = self.controller.card_frame("#FFFFFF")
        card_outer_layout = QVBoxLayout(card)
        card_outer_layout.setContentsMargins(0, 0, 0, 0)
        card_outer_layout.setSpacing(0)

        # ── Scroll area inside the card ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #F0F0F0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #999999; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(inner)
        form_layout.setContentsMargins(40, 30, 40, 30)
        form_layout.setSpacing(16)

        # ── Keychain section ──────────────────────────────────────────────────
        info = QLabel("VISIONSIGHT KEYCHAIN ACCESS")
        info.setFont(QFont(".AppleSystemUIFont", 22, QFont.Weight.Bold))
        info.setStyleSheet("color: #FFFFFF;")
        form_layout.addWidget(info)

        desc = QLabel(
            "Your Mac password is required to bypass the Lock Screen immediately upon facial recognition. "
            "This string is natively routed and encrypted deep inside the macOS Apple Keychain hardware enclave. "
            "It is strictly read-only by the Daemon and is never written to disk or transmitted."
        )
        desc.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Bold))
        desc.setStyleSheet("color: #4B5563;")
        desc.setWordWrap(True)
        form_layout.addWidget(desc)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("ENTER YOUR MAC LOGIN PASSWORD...")
        self.password_input.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        self.password_input.setMinimumHeight(54)
        self.password_input.setStyleSheet("""
            QLineEdit { padding: 16px 20px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: #FFFFFF; font-weight: 500; font-size: 16px; }
            QLineEdit:focus { background: rgba(255, 255, 255, 0.1); border: 1px solid #0A84FF; color: #FFFFFF; }
        """)
        form_layout.addWidget(self.password_input)

        btn_keychain = StyledButton("ENCRYPT TO APPLE KEYCHAIN", primary=True)
        btn_keychain.setMinimumHeight(54)
        btn_keychain.clicked.connect(self.controller.update_keychain_password)
        form_layout.addWidget(btn_keychain)

        # ── Divider ───────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("background: #2C2C2E; max-height: 3px; margin-top: 10px; margin-bottom: 10px;")
        form_layout.addWidget(divider)

        # ── Danger Zone ───────────────────────────────────────────────────────
        danger_label = QLabel("⚠  DANGER ZONE")
        danger_label.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        danger_label.setStyleSheet("""
            color: #FFFFFF;
            background: #FF5555;
            border: none; border-radius: 20px;
            padding: 8px 16px;
            letter-spacing: 2px;
        """)
        form_layout.addWidget(danger_label)

        danger_desc = QLabel(
            "These actions are IRREVERSIBLE. Reset All Data erases all biometric profiles, logs, and the saved "
            "password, then returns VisionSight to the initial setup state. "
            "Uninstall additionally removes the global CLI command and quits the application."
        )
        danger_desc.setFont(QFont(".AppleSystemUIFont", 13, QFont.Weight.Bold))
        danger_desc.setStyleSheet("color: #7F1D1D;")
        danger_desc.setWordWrap(True)
        form_layout.addWidget(danger_desc)

        danger_btns = QHBoxLayout()
        danger_btns.setSpacing(16)

        btn_reset = StyledButton("RESET ALL DATA", is_danger=True)
        btn_reset.setMinimumHeight(52)
        btn_reset.setToolTip("Erase all profiles, logs, env settings and keychain password — keeps CLI installed")
        btn_reset.clicked.connect(self.controller.reset_all_data)
        danger_btns.addWidget(btn_reset)

        btn_uninstall = StyledButton("UNINSTALL VISIONSIGHT", is_danger=True)
        btn_uninstall.setMinimumHeight(52)
        btn_uninstall.setToolTip("Reset all data AND remove the global CLI symlink + shell alias, then quit")
        btn_uninstall.setStyleSheet("""
            QPushButton {
                background: #2C2C2E;
                color: #FF5555;
                border: 3px solid #FF5555;
                font-size: 13px;
                font-weight: 900;
                padding: 10px 18px;
                letter-spacing: 1px;
            }
            QPushButton:hover { background: #FF5555; color: #FFFFFF; border: none; border-radius: 20px; }
            QPushButton:pressed { background: #CC0000; color: #FFFFFF; }
        """)
        btn_uninstall.clicked.connect(self.controller.uninstall_app)
        danger_btns.addWidget(btn_uninstall)

        form_layout.addLayout(danger_btns)
        form_layout.addStretch()

        scroll.setWidget(inner)
        card_outer_layout.addWidget(scroll)
        layout.addWidget(card, 1)


class LogsPage(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        header = QLabel("SYSTEM AUDIT")
        header.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        self.log_filter = QComboBox()
        self.log_filter.addItems(["ALL", "SUCCESS", "DENIED"])
        self.log_filter.setStyleSheet("""
            QComboBox {
                padding: 10px 16px;
                background: rgba(255, 255, 255, 0.05); color: #FFFFFF; 
                border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; font-size: 14px; font-weight: 600;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #FFFFFF;
                selection-background-color: #0A84FF;
                outline: none;
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
                color: #FFFFFF;
            }
            QTableWidget::item {
                padding: 15px;
                border-bottom: 2px solid #FFFFFF;
            }
            QTableWidget::item:selected {
                background-color: #0A84FF;
            }
            QHeaderView::section {
                background-color: transparent;
                padding: 15px;
                border: none;
                border-bottom: 2px solid #FFFFFF;
                font-weight: 900;
                color: #FFFFFF;
                font-size: 14px;
            }
        """)
        card_layout.addWidget(self.log_table)
        layout.addWidget(card, 1)


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
        t0.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
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
        self.lbl_cam_status.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        self.lbl_cam_status.setStyleSheet("color: #FFFFFF;")
        self.btn_grant_cam = StyledButton("GRANT CAMERA", primary=False)
        self.btn_grant_cam.clicked.connect(self.request_camera_access)
        cam_row.addWidget(self.lbl_cam_status)
        cam_row.addStretch()
        cam_row.addWidget(self.btn_grant_cam)
        w0_l.addLayout(cam_row)
        
        # Accessibility status row
        acc_row = QHBoxLayout()
        self.lbl_acc_status = QLabel("♿ ACCESSIBILITY PERMISSION: CHECKING...")
        self.lbl_acc_status.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        self.lbl_acc_status.setStyleSheet("color: #FFFFFF;")
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
        t1.setFont(QFont(".AppleSystemUIFont", 48, QFont.Weight.Bold))
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
        self.wiz_pass.setFont(QFont(".AppleSystemUIFont", 20, QFont.Weight.Bold))
        self.wiz_pass.setMinimumHeight(70)
        self.wiz_pass.setStyleSheet("QLineEdit { padding: 16px 20px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: #FFFFFF; font-weight: 500; font-size: 16px; } QLineEdit:focus { background: rgba(255, 255, 255, 0.1); border: 1px solid #0A84FF; color: #FFFFFF; }")
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
        t2.setFont(QFont(".AppleSystemUIFont", 32, QFont.Weight.Bold))
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w2_l.addWidget(t2)
        
        d2 = QLabel("Look directly at the camera. Ensure your face is clearly visible.")
        d2.setFont(QFont(".AppleSystemUIFont", 16, QFont.Weight.Bold))
        d2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w2_l.addWidget(d2)
        
        self.wiz_video = QLabel()
        self.wiz_video.setFixedSize(360, 270)
        self.wiz_video.setStyleSheet("background-color: #FFFFFF; border: none; border-radius: 20px;")
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
                border-radius: 20px;
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
        self.wiz_name.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        self.wiz_name.setStyleSheet("QLineEdit { padding: 16px 20px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: #FFFFFF; font-weight: 500; font-size: 16px; } QLineEdit:focus { background: rgba(255, 255, 255, 0.1); border: 1px solid #0A84FF; color: #FFFFFF; }")
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
