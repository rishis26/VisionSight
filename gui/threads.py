import os
import sys

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


class CameraThread(QThread):
    new_frame = pyqtSignal(QImage, object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self._run_flag = True
        self.cap = None
        self._handoff_mode = False

    def run(self):
        import cv2
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_AVFOUNDATION)
        if not self.cap.isOpened():
            self.cap = None
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

        if not self._handoff_mode:
            self.cap.release()
            self.cap = None

    def stop(self):
        self._run_flag = False
        self.wait()

    def stop_and_handoff(self):
        """Stop the preview loop but keep the VideoCapture alive and return it."""
        self._handoff_mode = True
        self._run_flag = False
        self.wait()
        cap = self.cap
        self.cap = None
        return cap


class ScanProcessThread(QThread):
    """
    Spawns face_auth/scan_worker.py as an isolated subprocess for each scan.

    WHY SUBPROCESS:
      dlib and cv2 load ~150 MB and cannot be unloaded from CPython once
      imported — C extensions are permanently mapped. Running the scan in a
      separate process lets the OS reclaim 100% of that memory when the
      subprocess exits. The main tray process stays at ~84 MB private memory
      permanently, regardless of how many scans have run.

    WHY QThread WRAPPER:
      We still need a non-blocking way to wait for the subprocess and deliver
      the result back to the Qt main thread via a signal without freezing the UI.
    """

    scan_complete = pyqtSignal(str, str)   # (result, authenticated_username)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None

    def run(self):
        import subprocess
        import json as _json
        from system import paths as _paths

        python_exe   = sys.executable
        worker_path  = os.path.join(str(_paths.get_base_dir()), "face_auth", "scan_worker.py")

        config_line = _json.dumps({
            "project_root": str(_paths.get_base_dir()),
            "env_path":     str(_paths.get_env_path()),
        }).encode() + b"\n"

        result    = "failed"
        auth_name = ""

        try:
            self._proc = subprocess.Popen(
                [python_exe, worker_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = self._proc.communicate(
                input=config_line, timeout=120
            )

            # Surface any worker-side diagnostics without polluting main logs
            if stderr_bytes:
                for line in stderr_bytes.decode(errors="replace").splitlines():
                    if line.strip():
                        print(f"[scan_worker] {line}", file=sys.stderr)

            if self._proc.returncode == 0 and stdout_bytes.strip():
                data      = _json.loads(stdout_bytes.strip())
                result    = data.get("result", "failed")
                auth_name = data.get("auth_name", "")

        except subprocess.TimeoutExpired:
            if self._proc:
                self._proc.kill()
                self._proc.wait()
            result = "aborted"

        except Exception as e:
            print(f"[ScanProcessThread] Unexpected error: {e}", file=sys.stderr)
            result = "failed"

        self.scan_complete.emit(result, auth_name)

    def abort(self):
        """Send SIGTERM to the scan subprocess to abort the current scan."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class DaemonScanThread(QThread):
    """
    In-process scan thread (kept for reference / manual GUI testing).
    Use ScanProcessThread for daemon-mode scans to get full memory reclamation.

    WHY QThread and not threading.Thread:
      cv2.VideoCapture() on Apple Silicon (macOS Sonoma) raises EXC_BAD_INSTRUCTION
      when called from a raw Python threading.Thread. QThreads are registered with
      the macOS CoreMedia / AVFoundation subsystem and are safe for camera access.
    """

    scan_complete = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system    = None
        self.verifier  = None
        self._existing_cap = None

    def run(self):
        if self.system is None:
            from system.lock import SystemController
            self.system = SystemController()
        if self.verifier is None:
            from face_auth.verify import FaceVerifier
            self.verifier = FaceVerifier(headless=True)

        try:
            self.verifier.reload_config()
            result = self.verifier.authenticate_once(
                self.system,
                use_esc_hook=False,
                defer_unlock=True,
                existing_cap=self._existing_cap,
            )
        except Exception as e:
            print(f"[DaemonScanThread] exception: {e}", file=sys.stderr)
            result = "failed"

        auth_name = ""
        if result == "success" and self.verifier.AUTO_UNLOCK:
            auth_name = self.verifier.auth_name or ""
        self.scan_complete.emit(result, auth_name)

    def abort(self):
        if self.verifier is not None:
            self.verifier._stop_requested = True
