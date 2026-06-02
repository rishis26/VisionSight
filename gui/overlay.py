import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
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
        
        # Ultra-Compact AirPods-Style Pill
        self.pill = QWidget()
        self.pill.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 230);
                border-radius: 18px;
            }
        """)
        
        self.pill.setFixedSize(220, 36)
        
        # Extremely soft, barely-there shadow
        shadow = QGraphicsDropShadowEffect(self.pill)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.pill.setGraphicsEffect(shadow)
        
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(14, 0, 14, 0)
        pill_layout.setSpacing(10)
        
        # Tiny green check or dot
        dot = QWidget()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("""
            background-color: #34C759;
            border-radius: 4px;
        """)
        
        title = QLabel(f"Unlocked • {username}")
        title.setFont(QFont(".AppleSystemUIFont", 12, QFont.Weight.Medium))
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        
        pill_layout.addWidget(dot)
        pill_layout.addWidget(title)
        pill_layout.addStretch()
        
        layout.addWidget(self.pill)
        
        screen = QApplication.primaryScreen().geometry()
        
        # Window size tightly wraps the pill + shadow margin
        self.start_y = 0
        self.end_y = 30
        self.x_pos = (screen.width() - 260) // 2
        
        self.setGeometry(self.x_pos, self.start_y, 260, 80)
        self.setWindowOpacity(0.0)

    def animate_in(self):
        self.anim_pos = QPropertyAnimation(self, b"geometry")
        self.anim_pos.setDuration(800)
        self.anim_pos.setStartValue(QRect(self.x_pos, self.start_y, 260, 80))
        self.anim_pos.setEndValue(QRect(self.x_pos, self.end_y, 260, 80))
        self.anim_pos.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        self.anim_op = QVariantAnimation(self)
        self.anim_op.setDuration(800)
        self.anim_op.setStartValue(0.0)
        self.anim_op.setEndValue(1.0)
        self.anim_op.valueChanged.connect(self.setWindowOpacity)
        
        self.anim_pos.start()
        self.anim_op.start()
        
        QTimer.singleShot(2300, self.animate_out)
        
    def animate_out(self):
        self.anim_pos_out = QPropertyAnimation(self, b"geometry")
        self.anim_pos_out.setDuration(600)
        self.anim_pos_out.setStartValue(QRect(self.x_pos, self.end_y, 260, 80))
        self.anim_pos_out.setEndValue(QRect(self.x_pos, self.start_y, 260, 80))
        self.anim_pos_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim_op_out = QVariantAnimation(self)
        self.anim_op_out.setDuration(600)
        self.anim_op_out.setStartValue(1.0)
        self.anim_op_out.setEndValue(0.0)
        self.anim_op_out.valueChanged.connect(self.setWindowOpacity)
        
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
    QTimer.singleShot(1500, window.animate_in)
    sys.exit(app.exec())
