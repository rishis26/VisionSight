import os
import sys
import threading

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


def _drain_stderr(proc):
    """
    Drain subprocess stderr line-by-line in a daemon thread.
    Prevents the OS pipe buffer from filling up and deadlocking the subprocess.
    """
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
    """
    Runs face_auth/scan_worker.py as an isolated subprocess.

    ┌─ Two modes ──────────────────────────────────────────────────────────────┐
    │  immediate=False  (WARMUP)                                               │
    │    Spawned early (display asleep + screen locked).                       │
    │    Subprocess imports Python + dlib in background — NO camera yet.       │
    │    trigger_scan() is called when display wakes → camera opens then.      │
    │    Wait from display-wake to first frame: ~1-2 s (only camera init).     │
    │                                                                          │
    │  immediate=True   (COLD START)                                           │
    │    Fallback when no warmup subprocess is available.                      │
    │    Python + dlib + camera all init in sequence: ~5-8 s total.            │
    └──────────────────────────────────────────────────────────────────────────┘

    WHY SUBPROCESS:
      dlib and cv2 are C extensions that cannot be unloaded from CPython once
      imported. Subprocess isolation lets the OS reclaim all face-recognition
      memory (~150 MB) when the process exits after each scan.

    WHY QThread WRAPPER:
      Non-blocking wait + signal delivery back to the Qt main thread.
    """

    scan_complete = pyqtSignal(str, str)   # (result, authenticated_username)

    def __init__(self, parent=None, immediate=False):
        super().__init__(parent)
        self._proc            = None
        self._phase           = "prewarming"   # prewarming | ready | scanning | done
        self._scan_event      = threading.Event()
        self._abort_requested = False

        if immediate:
            # Trigger scan as soon as subprocess signals ready
            self._scan_event.set()

    # ── public API (called from main thread) ──────────────────────────────────

    def trigger_scan(self):
        """Tell the subprocess to start scanning. Thread-safe."""
        self._scan_event.set()

    def abort(self):
        """Kill the subprocess immediately, regardless of phase."""
        self._abort_requested = True
        self._scan_event.set()          # unblock any wait()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    # ── QThread entry point ───────────────────────────────────────────────────

    def run(self):
        import subprocess
        import json as _json
        from system import paths as _paths

        base_dir    = str(_paths.get_base_dir())
        worker_path = os.path.join(base_dir, "face_auth", "scan_worker.py")
        config_line = (_json.dumps({
            "project_root": base_dir,
            "env_path":     str(_paths.get_env_path()),
        }) + "\n").encode()

        result    = "failed"
        auth_name = ""

        # Prefer the project's own venv Python — it has all packages installed
        # (cv2, dlib, face_recognition).  Fall back to sys.executable only if
        # the venv doesn't exist (e.g. system-wide install).
        venv_python = os.path.join(base_dir, ".venv", "bin", "python3")
        python_exe  = venv_python if os.path.isfile(venv_python) else sys.executable

        try:
            self._proc = subprocess.Popen(
                [python_exe, worker_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Drain stderr asynchronously to prevent pipe buffer deadlock
            threading.Thread(
                target=_drain_stderr, args=(self._proc,), daemon=True
            ).start()

            # ── Phase 1: send config ──────────────────────────────────────────
            # Worker imports Python + dlib here (slow, ~3-5 s).
            # Camera is NOT opened yet.
            self._proc.stdin.write(config_line)
            self._proc.stdin.flush()

            # Wait for worker to finish importing ("ready\n" → dlib loaded)
            ready_line = self._proc.stdout.readline().decode().strip()
            if ready_line != "ready":
                # Worker crashed during import
                self._proc.wait()
                self.scan_complete.emit("failed", "")
                return

            self._phase = "ready"

            # ── Phase 2: wait for scan trigger ────────────────────────────────
            # In warmup mode: block here until trigger_scan() is called.
            # In immediate mode: _scan_event was pre-set, so this returns instantly.
            self._scan_event.wait(timeout=600)   # 10-minute idle limit

            if self._abort_requested:
                # Tell worker to exit cleanly
                try:
                    self._proc.stdin.write(b"abort\n")
                    self._proc.stdin.flush()
                    self._proc.stdout.readline()  # drain result line
                except Exception:
                    pass
                if self._proc.poll() is None:
                    self._proc.terminate()
                self._proc.wait()
                self.scan_complete.emit("aborted", "")
                return

            # ── Phase 3: trigger scan ─────────────────────────────────────────
            # Worker opens camera here (AVFoundation init: ~1-2 s).
            # Camera LED turns on NOW, not before.
            self._phase = "scanning"
            self._proc.stdin.write(b"scan\n")
            self._proc.stdin.flush()

            # Block until scan finishes and result arrives
            result_raw = self._proc.stdout.readline().decode().strip()
            if result_raw:
                data      = _json.loads(result_raw)
                result    = data.get("result", "failed")
                auth_name = data.get("auth_name", "")

            self._proc.wait()

        except subprocess.TimeoutExpired:
            if self._proc:
                self._proc.kill()
                self._proc.wait()
            result = "aborted"
        except Exception as e:
            print(f"[ScanProcessThread] Unexpected error: {e}", file=sys.stderr)
            result = "failed"

        self._phase = "done"
        self.scan_complete.emit(result, auth_name)


class DaemonScanThread(QThread):
    """
    Legacy in-process scan thread (kept for reference / manual GUI testing).
    Use ScanProcessThread for daemon-mode scans — it frees dlib memory after
    each scan whereas this class keeps dlib permanently resident.
    """

    scan_complete = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.system        = None
        self.verifier      = None
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
