"""
Standalone face-recognition worker — spawned by VisionSight for each scan.

Two-phase protocol:
  Phase 1 (import):  stdin  ← JSON config
                     stdout → "ready"    (dlib loaded, NO camera)

  Phase 2 (scan):    stdin  ← "scan" | "abort"
                     stdout → JSON result {"result": ..., "auth_name": ...}

All diagnostic prints are redirected to stderr so they never corrupt stdout.
"""

import sys
import os
import json


def _write(line: str):
    """Write one line to the real stdout (even when sys.stdout is redirected)."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def main():
    # ── 1. Read config ────────────────────────────────────────────────────────
    raw = sys.stdin.readline()
    if not raw.strip():
        _write("ready")
        _write(json.dumps({"result": "failed", "auth_name": ""}))
        return

    try:
        config = json.loads(raw)
    except Exception:
        _write("ready")
        _write(json.dumps({"result": "failed", "auth_name": ""}))
        return

    project_root = config.get("project_root", "")
    env_path     = config.get("env_path", "")

    # ── 2. Add project to path ────────────────────────────────────────────────
    if project_root and project_root not in sys.path:
        sys.path.insert(0, project_root)

    # ── 3. Redirect print() to stderr so stdout channel stays clean ───────────
    _real_stdout = sys.stdout
    sys.stdout   = sys.stderr

    # ── 4. Load env ───────────────────────────────────────────────────────────
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except Exception:
        pass

    # ── 5. Import heavy deps (dlib / cv2 / face_recognition) ─────────────────
    try:
        from face_auth.verify import FaceVerifier
        from system.lock import SystemController
    except Exception as e:
        print(f"[scan_worker] import error: {e}", file=sys.stderr)
        sys.stdout = _real_stdout
        _write("ready")
        _write(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # ── 6. Initialise objects (loads face encodings; camera still NOT open) ───
    try:
        system   = SystemController()
        verifier = FaceVerifier(headless=True)
    except Exception as e:
        print(f"[scan_worker] init error: {e}", file=sys.stderr)
        sys.stdout = _real_stdout
        _write("ready")
        _write(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # ── 7. Signal ready — dlib is loaded, camera LED is still off ─────────────
    sys.stdout = _real_stdout
    _write("ready")
    sys.stdout = sys.stderr

    # ── 8. Wait for scan or abort command ────────────────────────────────────
    try:
        cmd = sys.stdin.readline().strip()
    except Exception:
        cmd = ""

    if cmd != "scan":
        sys.stdout = _real_stdout
        _write(json.dumps({"result": "aborted", "auth_name": ""}))
        return

    # ── 9. Open camera (LED turns on HERE — display is already on) ────────────
    result    = "failed"
    auth_name = ""
    cap       = None

    try:
        import cv2
        cam_idx = int(os.getenv("VISIONSIGHT_CAMERA", "0"))
        cap = cv2.VideoCapture(cam_idx, cv2.CAP_AVFOUNDATION)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # keep only the freshest frame

        if not cap.isOpened():
            print("[scan_worker] Failed to open camera", file=sys.stderr)
            sys.stdout = _real_stdout
            _write(json.dumps({"result": "failed", "auth_name": ""}))
            return

        # Drain 1 startup frame to ensure live frame buffer
        cap.grab()

    except Exception as e:
        print(f"[scan_worker] camera error: {e}", file=sys.stderr)
        if cap:
            try:
                cap.release()
            except Exception:
                pass
        sys.stdout = _real_stdout
        _write(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # ── 10. Run face recognition ──────────────────────────────────────────────
    try:
        result = verifier.authenticate_once(
            system,
            use_esc_hook=False,
            defer_unlock=True,    # parent process does the actual unlock
            existing_cap=cap,     # hand off warm cap — no re-init inside
        )
        if result == "success" and verifier.AUTO_UNLOCK:
            auth_name = verifier.auth_name or ""
    except Exception as e:
        print(f"[scan_worker] scan error: {e}", file=sys.stderr)
        result = "failed"
        try:
            cap.release()
        except Exception:
            pass

    # ── 11. Send result and exit ──────────────────────────────────────────────
    # On exit the OS reclaims ALL dlib / cv2 / face_recognition memory,
    # returning the parent tray process to its ~84 MB private-memory baseline.
    sys.stdout = _real_stdout
    _write(json.dumps({"result": result, "auth_name": auth_name}))


if __name__ == "__main__":
    main()
