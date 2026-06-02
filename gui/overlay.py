import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QVariantAnimation
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QPainterPath

class UnlockOverlay(QWidget):
    def __init__(self, username):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.ToolTip |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.pill = QWidget()
        self.pill.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-radius: 24px;
                border: 1px solid #E5E5EA;
            }
        """)
        
        # Add subtle drop shadow to the pill
        shadow = QGraphicsDropShadowEffect(self.pill)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 6)
        self.pill.setGraphicsEffect(shadow)
        
        self.pill.setFixedSize(320, 48)
        
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(20, 0, 20, 0)
        pill_layout.setSpacing(12)
        
        icon = QLabel("●")
        icon.setFont(QFont(".AppleSystemUIFont", 12))
        icon.setStyleSheet("color: #007AFF; background: transparent;")
        
        text = QLabel(f"Verified: {username}")
        text.setFont(QFont(".AppleSystemUIFont", 14, QFont.Weight.Medium))
        text.setStyleSheet("color: #000000; background: transparent;")
        
        pill_layout.addWidget(icon)
        pill_layout.addWidget(text)
        pill_layout.addStretch()
        
        layout.addWidget(self.pill)
        
        screen = QApplication.primaryScreen().geometry()
        self.start_y = 0
        self.end_y = 45
        self.x_pos = (screen.width() - 340) // 2
        
        self.setGeometry(self.x_pos, self.start_y, 340, 68)
        
        self.setWindowOpacity(0.0)

    def animate_in(self):
        self.anim_pos = QPropertyAnimation(self, b"geometry")
        self.anim_pos.setDuration(500)
        self.anim_pos.setStartValue(QRect(self.x_pos, self.start_y, 340, 68))
        self.anim_pos.setEndValue(QRect(self.x_pos, self.end_y, 340, 68))
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        self.anim_op = QPropertyAnimation(self, b"windowOpacity")
        self.anim_op.setDuration(500)
        self.anim_op.setStartValue(0.0)
        self.anim_op.setEndValue(1.0)
        
        self.anim_pos.start()
        self.anim_op.start()
        
        QTimer.singleShot(2500, self.animate_out)
        
    def animate_out(self):
        self.anim_pos_out = QPropertyAnimation(self, b"geometry")
        self.anim_pos_out.setDuration(500)
        self.anim_pos_out.setStartValue(QRect(self.x_pos, self.end_y, 340, 68))
        self.anim_pos_out.setEndValue(QRect(self.x_pos, self.start_y, 340, 68))
        self.anim_pos_out.setEasingCurve(QEasingCurve.Type.InBack)
        
        self.anim_op_out = QPropertyAnimation(self, b"windowOpacity")
        self.anim_op_out.setDuration(500)
        self.anim_op_out.setStartValue(1.0)
        self.anim_op_out.setEndValue(0.0)
        
        self.anim_pos_out.finished.connect(QApplication.quit)
        
        self.anim_pos_out.start()
        self.anim_op_out.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except ImportError:
        pass

    username = sys.argv[1] if len(sys.argv) > 1 else "USER"
    window = UnlockOverlay(username)
    window.show()
    window.animate_in()
    sys.exit(app.exec())
