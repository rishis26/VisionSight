import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QFrame, QWidget, QPushButton, QGraphicsDropShadowEffect, QApplication, QStyle, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize, QRect, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient, QPainterPath

# ==========================================
# LIQUID MORPHISM (NEUMORPHISM) DESIGN SYSTEM
# ==========================================

LIQUID_BG = "#E0E5EC"
SHADOW_DARK = QColor(163, 177, 198, 170)  # Bottom-right shadow
SHADOW_LIGHT = QColor(255, 255, 255, 255) # Top-left shadow (Highlight)

def apply_neumorphic_shadow(widget, radius=12, offset=6):
    """Applies the dark bottom-right shadow. The top-left is handled via painting or borders."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setColor(SHADOW_DARK)
    shadow.setOffset(offset, offset)
    widget.setGraphicsEffect(shadow)

class LiquidFrame(QFrame):
    """A container that looks softly extruded from the background."""
    def __init__(self, parent=None, radius=24):
        super().__init__(parent)
        self.radius = radius
        self.setStyleSheet("background-color: transparent;")
        apply_neumorphic_shadow(self, 20, 8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base background
        painter.setBrush(QBrush(QColor(LIQUID_BG)))
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, self.radius, self.radius)
        
        # Draw the top-left highlight to complete the Neumorphic effect
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)
        
        pen = QPen(SHADOW_LIGHT, 4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # We draw the highlight by shifting the rect slightly down-right
        painter.drawPath(path.translated(-1.5, -1.5))

class LiquidInput(QFrame):
    """An inset liquid container for inputs."""
    def __init__(self, parent=None, radius=16):
        super().__init__(parent)
        self.radius = radius
        self.setStyleSheet("background-color: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base background
        painter.setBrush(QBrush(QColor("#D1D8E0"))) # Slightly darker for inset
        painter.setPen(Qt.PenStyle.NoPen)
        rect = self.rect()
        painter.drawRoundedRect(rect, self.radius, self.radius)
        
        # Draw inset shadow (top-left dark, bottom-right light)
        pen_dark = QPen(SHADOW_DARK, 3)
        painter.setPen(pen_dark)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, 0, 0), self.radius, self.radius)

        pen_light = QPen(SHADOW_LIGHT, 3)
        painter.setPen(pen_light)
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), self.radius, self.radius)

class ToggleButton(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 32)
        self._checked = checked
        self._thumb_pos = self.width() - 28 if checked else 4
        
        self.animation = QPropertyAnimation(self, b"thumb_pos")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(250)

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
        
        # Inset Track
        track_color = QColor("#007AFF") if self._checked else QColor("#D1D8E0")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        
        # Inner shadow on track
        painter.setPen(QPen(QColor(0,0,0, 40), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        
        # Thumb (Liquid Drop)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(LIQUID_BG)))
        thumb_rect = QRectF(self._thumb_pos, 4, 24, 24)
        painter.drawEllipse(thumb_rect)
        
        # Thumb shadow to make it pop
        painter.setPen(QPen(SHADOW_LIGHT, 2))
        painter.drawEllipse(thumb_rect.translated(-1, -1))

class StyledButton(QPushButton):
    def __init__(self, text, primary=True, is_danger=False):
        super().__init__(text)
        self.primary = primary
        self.is_danger = is_danger
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)
        self.update_style()
        apply_neumorphic_shadow(self, 15, 4)

    def update_style(self):
        if self.is_danger:
            self.bg_color = QColor("#FF3B30")
            self.text_color = "#FFFFFF"
        elif self.primary:
            self.bg_color = QColor("#007AFF")
            self.text_color = "#FFFFFF"
        else:
            self.bg_color = QColor(LIQUID_BG)
            self.text_color = "#4A5568"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.text_color};
                font-size: 15px;
                font-weight: 800;
                border: none;
            }}
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = 25
        
        # Liquid Gradient Background
        grad = QLinearGradient(0, 0, self.width(), self.height())
        if self.isDown():
            grad.setColorAt(0, self.bg_color.darker(110))
            grad.setColorAt(1, self.bg_color.lighter(110))
        else:
            grad.setColorAt(0, self.bg_color.lighter(110))
            grad.setColorAt(1, self.bg_color.darker(110))
            
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # Highlight rim
        if not self.isDown():
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), radius, radius)
            pen = QPen(QColor(255, 255, 255, 120), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path.translated(-1, -1))

        super().paintEvent(event)

class NavButton(QPushButton):
    def __init__(self, text, idx, callback, icon_enum=None):
        super().__init__(text)
        self.idx = idx
        self.callback = callback
        self.setFixedHeight(48)
        if icon_enum:
            self.setIcon(QApplication.style().standardIcon(icon_enum))
            self.setIconSize(QSize(20, 20))
            
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_active = False
        self.update_appearance()
        self.clicked.connect(self.on_click)
        
    def on_click(self):
        self.callback(self.idx)
        
    def set_active(self, is_active):
        self.is_active = is_active
        if is_active:
            apply_neumorphic_shadow(self, 10, 3)
        else:
            self.setGraphicsEffect(None)
        self.update_appearance()

    def update_appearance(self):
        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding: 0 20px;
                    background-color: transparent;
                    color: #007AFF; font-size: 14px; font-weight: 800;
                    border: none;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding: 0 20px;
                    background-color: transparent;
                    color: #718096; font-size: 14px; font-weight: 600;
                    border: none;
                }}
                QPushButton:hover {{ color: #2D3748; }}
            """)

    def paintEvent(self, event):
        if self.is_active:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.rect()
            radius = 24
            
            painter.setBrush(QBrush(QColor(LIQUID_BG)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, radius, radius)
            
            # Top-left highlight
            path = QPainterPath()
            path.addRoundedRect(QRectF(rect), radius, radius)
            painter.setPen(QPen(SHADOW_LIGHT, 3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path.translated(-1, -1))
            
        super().paintEvent(event)
