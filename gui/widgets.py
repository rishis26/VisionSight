import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QFrame, QWidget, QPushButton, QGraphicsDropShadowEffect, QApplication, QStyle, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize, QRect, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient, QPainterPath

APPLE_BG = "#000000"         # Pitch black background
APPLE_CARD = "#1C1C1E"       # Elevated card background (iOS dark gray)
APPLE_ACCENT = "#007AFF"     # Apple System Blue
APPLE_TEXT = "#FFFFFF"       # Primary text
APPLE_SUBTEXT = "#8E8E93"    # Secondary text

def apply_apple_shadow(widget, radius=20, offset=4, alpha=80):
    """Subtle, sharp shadow for elevated cards against the pure black background."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setColor(QColor(0, 0, 0, alpha))
    shadow.setOffset(0, offset)
    widget.setGraphicsEffect(shadow)

class GlassCard(QFrame):
    """Clean dark mode card."""
    def __init__(self, parent=None, radius=12):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #2C2C2E;
                border: none;
                border-radius: {radius}px;
            }}
        """)
        apply_apple_shadow(self, radius=20, offset=4, alpha=40)

class ToggleButton(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 32)
        self._checked = checked
        self._thumb_pos = self.width() - 28 if checked else 4
        
        self.animation = QPropertyAnimation(self, b"thumb_pos")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(200)

    def isChecked(self):
        return self._checked

    def setCheckedNoSignal(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.start_transition()

    def start_transition(self):
        self.animation.stop()
        if self._checked:
            self.animation.setEndValue(self.width() - 28)
        else:
            self.animation.setEndValue(4)
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
        track_color = QColor(APPLE_ACCENT) if self._checked else QColor("#39393D")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        
        # Thumb
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        thumb_rect = QRectF(self._thumb_pos, 4, 24, 24)
        painter.drawEllipse(thumb_rect)
        
        # Sharp shadow for the thumb
        painter.setPen(QPen(QColor(0,0,0, 40), 1))
        painter.drawEllipse(thumb_rect)

class StyledButton(QPushButton):
    def __init__(self, text, primary=True, is_danger=False):
        super().__init__(text)
        self.primary = primary
        self.is_danger = is_danger
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.update_style()

    def update_style(self):
        if self.is_danger:
            bg = "#FF3B30"
            text_color = "#FFFFFF"
        elif self.primary:
            bg = APPLE_ACCENT
            text_color = "#FFFFFF"
        else:
            bg = "#2C2C2E"
            text_color = APPLE_ACCENT
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                font-size: 16px;
                font-weight: 700;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:pressed {{
                background-color: {bg};
                margin: 2px;
            }}
        """)

class NavButton(QPushButton):
    def __init__(self, text, idx, callback, icon_enum=None):
        super().__init__(text)
        self.idx = idx
        self.callback = callback
        self.setFixedHeight(48)
        if icon_enum:
            self.setIcon(QApplication.style().standardIcon(icon_enum))
            self.setIconSize(QSize(22, 22))
            
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_active = False
        self.update_appearance()
        self.clicked.connect(self.on_click)
        
    def on_click(self):
        self.callback(self.idx)
        
    def set_active(self, is_active):
        self.is_active = is_active
        self.update_appearance()

    def update_appearance(self):
        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding: 0 20px;
                    background-color: #1C1C1E;
                    color: {APPLE_ACCENT}; font-size: 15px; font-weight: 800;
                    border: none;
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding: 0 20px;
                    background-color: transparent;
                    color: {APPLE_SUBTEXT}; font-size: 15px; font-weight: 600;
                    border: none;
                    border-radius: 12px;
                }}
                QPushButton:hover {{ color: #FFFFFF; background-color: #1C1C1E; }}
            """)
