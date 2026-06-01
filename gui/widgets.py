from PyQt6.QtWidgets import QFrame, QWidget, QPushButton, QGraphicsDropShadowEffect, QApplication, QStyle
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QSize
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen

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
