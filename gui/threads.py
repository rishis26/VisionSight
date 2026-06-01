from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class CameraThread(QThread):
    new_frame = pyqtSignal(QImage, object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._run_flag = True
        self.cap = None

    def run(self):
        import cv2
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
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
            self.msleep(5)
            
        self.cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class DaemonScanThread(QThread):
    """
    Runs the blocking face-recognition camera scan as a Qt-managed thread.

    WHY QThread and not threading.Thread:
      cv2.VideoCapture() on Apple Silicon (macOS Sonoma) raises EXC_BAD_INSTRUCTION
      when called from a raw Python threading.Thread. QThreads are registered with
      the macOS CoreMedia / AVFoundation subsystem and are safe for camera access.
    """

    scan_complete = pyqtSignal(str, str)  # (result, authenticated_username)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = None
        self.verifier = None

    def run(self):
        """Blocking scan. Runs on this QThread's execution context.

        defer_unlock=True: simulate_unlock() uses CGEventPost(kCGHIDEventTap)
        which SILENTLY FAILS when called from a background QThread on macOS.
        We defer the unlock to the main thread via the scan_complete signal.
        """
        if self.system is None:
            from system.lock import SystemController
            self.system = SystemController()
        if self.verifier is None:
            from face_auth.verify import FaceVerifier
            self.verifier = FaceVerifier(headless=True)
            
        try:
            self.verifier.reload_config()
            result = self.verifier.authenticate_once(
                self.system, use_esc_hook=False, defer_unlock=True
            )
        except Exception as e:
            print(f"⚠️ DaemonScanThread exception: {e}")
            result = "failed"

        auth_name = ""
        if result == "success" and self.verifier.AUTO_UNLOCK:
            auth_name = self.verifier.auth_name or ""
        self.scan_complete.emit(result, auth_name)

    def abort(self):
        """Thread-safe abort: sets a flag the verifier checks each frame."""
        if self.verifier is not None:
            self.verifier._stop_requested = True

