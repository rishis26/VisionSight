"""
Standalone face-recognition worker — spawned by VisionSight for each scan.

Because this process exits after every scan, the OS reclaims 100% of
dlib/cv2 memory on exit. The parent tray process never loads these libs
and permanently stays at its ~84 MB private-memory baseline.

Two-phase protocol (line-oriented over stdin / stdout):
  Phase 1 — import:
    stdin  ← JSON config {"project_root": "...", "env_path": "..."}
    stdout → "ready"     (dlib loaded, camera NOT open yet)

  Phase 2 — scan:
    stdin  ← "scan" | "abort"
    stdout → JSON result {"result": "success"|"rejected"|"aborted"|"failed",
                          "auth_name": "<name>"|""}

All diagnostic prints (FaceVerifier logs etc.) are redirected to stderr so
they never corrupt the stdout channel.
"""

import sys
import os
import json


def main():
    # ── 1. Read config from parent ────────────────────────────────────────────
    raw = sys.stdin.readline()
    if not raw.strip():
        _write_stdout("ready")          # still need to ack so parent doesn't hang
        _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
        return

    try:
        config = json.loads(raw)
    except Exception as e:
        _write_stdout("ready")
        _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
        return

    project_root = config.get("project_root", "")
    env_path     = config.get("env_path", "")

    # ── 2. Make VisionSight modules importable ────────────────────────────────
    if project_root and project_root not in sys.path:
        sys.path.insert(0, project_root)

    # ── 3. Redirect print() to stderr so stdout stays clean ──────────────────
    _real_stdout = sys.stdout
    sys.stdout   = sys.stderr   # FaceVerifier / dlib prints → stderr (invisible to parent)

    # ── 4. Load environment settings ─────────────────────────────────────────
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except Exception:
        pass

    # ── 5. Import heavy deps (only in this subprocess) ───────────────────────
    import_ok = True
    try:
        from face_auth.verify import FaceVerifier
        from system.lock import SystemController
    except Exception as e:
        print(f"[scan_worker] import error: {e}", file=sys.stderr)
        import_ok = False

    if not import_ok:
        sys.stdout = _real_stdout
        _write_stdout("ready")   # ack so parent doesn't hang forever
        _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # Create objects (loads encodings; camera still NOT open)
    try:
        system   = SystemController()
        verifier = FaceVerifier(headless=True)
    except Exception as e:
        print(f"[scan_worker] init error: {e}", file=sys.stderr)
        sys.stdout = _real_stdout
        _write_stdout("ready")
        _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # ── 6. Signal ready (dlib loaded, camera NOT open yet) ───────────────────
    sys.stdout = _real_stdout
    _write_stdout("ready")
    sys.stdout = sys.stderr   # redirect again for scan output

    # ── 7. Wait for scan or abort command ────────────────────────────────────
    cmd = ""
    try:
        cmd = sys.stdin.readline().strip()
    except Exception:
        pass

    if cmd != "scan":
        sys.stdout = _real_stdout
        _write_stdout(json.dumps({"result": "aborted", "auth_name": ""}))
        return

    # ── 8. Open camera as fast as possible ───────────────────────────────────
    # Camera LED turns on HERE (display is already on — this is expected).
    # We open it explicitly so we can:
    #   a) set BUFFERSIZE=1 (prevents reading stale dark frames)
    #   b) drain the initial blank AVFoundation startup frames quickly
    #   c) pass the already-open cap to authenticate_once (no re-init inside)
    result    = "failed"
    auth_name = ""

    try:
        import cv2 as _cv2
        cam_idx = int(os.getenv("VISIONSIGHT_CAMERA", "0"))
        cap = _cv2.VideoCapture(cam_idx, _cv2.CAP_AVFOUNDATION)
        cap.set(_cv2.CAP_PROP_BUFFERSIZE, 1)   # keep only the latest frame

        if not cap.isOpened():
            print("[scan_worker] Could not open camera", file=sys.stderr)
            sys.stdout = _real_stdout
            _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
            return

        # Apply user-configured resolution (default 640x480 = AVFoundation native)
        res = os.getenv("VISIONSIGHT_RESOLUTION", "640x480")
        if res == "1280x720":
            cap.set(_cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(_cv2.CAP_PROP_FRAME_HEIGHT, 720)
        elif res != "640x480":
            try:
                w, h = map(int, res.split("x"))
                cap.set(_cv2.CAP_PROP_FRAME_WIDTH, w)
                cap.set(_cv2.CAP_PROP_FRAME_HEIGHT, h)
            except Exception:
                pass

        # Drain early blank/dark frames so authenticate_once starts on live data.
        # AVFoundation typically needs 2-4 reads before exposing properly.
        for _ in range(4):
            cap.grab()   # grab without decode — cheapest possible discard

    except Exception as e:
        print(f"[scan_worker] camera open error: {e}", file=sys.stderr)
        sys.stdout = _real_stdout
        _write_stdout(json.dumps({"result": "failed", "auth_name": ""}))
        return

    # ── 9. Run the scan ───────────────────────────────────────────────────────
    try:
        result = verifier.authenticate_once(
            system,
            use_esc_hook=False,
            defer_unlock=True,   # parent process handles the actual unlock
            existing_cap=cap,    # hand off warm camera — no re-init inside
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

    # ── 10. Send result and exit ──────────────────────────────────────────────
    sys.stdout = _real_stdout
    _write_stdout(json.dumps({"result": result, "auth_name": auth_name}))
    # Process exits → OS reclaims all dlib / cv2 / numpy / face_recognition memory


def _write_stdout(line: str):
    """Write a single line to the REAL stdout (not the stderr-redirected one)."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
