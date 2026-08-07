import os
import sys
import threading

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


def _drain_stderr(proc):
    try:
        for raw_line in proc.stderr:
            txt = raw_line.decode(errors="replace").strip()
            if txt:
                print(f"[scan_worker] {txt}", file=sys.stderr)
    except Exception:
        pass


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
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

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
        self._handoff_mode = True
        self._run_flag = False
        self.wait()
        cap = self.cap
        self.cap = None
        return cap


class ScanProcessThread(QThread):
    scan_complete = pyqtSignal(str, str)

    def __init__(self, parent=None, immediate=False):
        super().__init__(parent)
        self._proc = None
        self._phase = "prewarming"
        self._scan_event = threading.Event()
        self._abort_requested = False

        if immediate:
            self._scan_event.set()

    def trigger_scan(self):
        self._scan_event.set()

    def abort(self):
        self._abort_requested = True
        self._scan_event.set()
        if self._proc:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
            except Exception:
                pass

    def run(self):
        import subprocess
        import json as _json
        from system import paths as _paths

        base_dir = str(_paths.get_base_dir())
        worker_path = os.path.join(base_dir, "face_auth", "scan_worker.py")
        config_line = (_json.dumps({
            "project_root": base_dir,
            "env_path": str(_paths.get_env_path()),
        }) + "\n").encode()

        result = "failed"
        auth_name = ""

        venv_python = os.path.join(base_dir, ".venv", "bin", "python3")
        python_exe = venv_python if os.path.isfile(venv_python) else sys.executable

        try:
            self._proc = subprocess.Popen(
                [python_exe, worker_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            threading.Thread(
                target=_drain_stderr, args=(self._proc,), daemon=True
            ).start()

            try:
                self._proc.stdin.write(config_line)
                self._proc.stdin.flush()
            except Exception:
                pass

            try:
                ready_line = self._proc.stdout.readline().decode().strip()
            except Exception:
                ready_line = ""

            if self._abort_requested or ready_line != "ready":
                if self._proc and self._proc.poll() is None:
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=1.0)
                    except Exception:
                        pass
                self._phase = "done"
                self.scan_complete.emit("aborted" if self._abort_requested else "failed", "")
                return

            self._phase = "ready"
            self._scan_event.wait()

            if self._abort_requested:
                try:
                    self._proc.stdin.write(b"abort\n")
                    self._proc.stdin.flush()
                except Exception:
                    pass
                if self._proc and self._proc.poll() is None:
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=1.0)
                    except Exception:
                        pass
                self._phase = "done"
                self.scan_complete.emit("aborted", "")
                return

            self._phase = "scanning"
            try:
                self._proc.stdin.write(b"scan\n")
                self._proc.stdin.flush()
            except Exception:
                pass

            try:
                result_raw = self._proc.stdout.readline().decode().strip()
                if result_raw:
                    data = _json.loads(result_raw)
                    result = data.get("result", "failed")
                    auth_name = data.get("auth_name", "")
            except Exception as e:
                print(f"[ScanProcessThread] Read error: {e}", file=sys.stderr)

            if self._proc:
                try:
                    self._proc.wait(timeout=3.0)
                except Exception:
                    if self._proc.poll() is None:
                        self._proc.kill()

        except Exception as e:
            print(f"[ScanProcessThread] Unexpected error: {e}", file=sys.stderr)
            result = "failed"
        finally:
            if self._proc:
                for pipe in (self._proc.stdin, self._proc.stdout, self._proc.stderr):
                    if pipe:
                        try:
                            pipe.close()
                        except:
                            pass
                if self._proc.poll() is None:
                    try:
                        self._proc.kill()
                    except:
                        pass

        self._phase = "done"
        self.scan_complete.emit(result, auth_name)


class DaemonScanThread(QThread):
    scan_complete = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = None
        self.verifier = None
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
            print(f"[DaemonScanThread] Exception: {e}", file=sys.stderr)
            result = "failed"

        auth_name = ""
        if result == "success" and self.verifier.AUTO_UNLOCK:
            auth_name = self.verifier.auth_name or ""
        self.scan_complete.emit(result, auth_name)

    def abort(self):
        if self.verifier is not None:
            self.verifier._stop_requested = True
