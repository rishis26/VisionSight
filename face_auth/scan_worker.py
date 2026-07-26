"""
Standalone face-recognition worker — spawned by VisionSight for each scan.

Because this script exits after every scan, the OS reclaims 100% of dlib
and cv2 memory on exit. The parent tray process never loads these libraries
and permanently stays at its ~84 MB private-memory baseline.

Protocol (line-oriented JSON over stdin / stdout):
  stdin  ← single JSON line with {"project_root": "...", "env_path": "..."}
  stdout → single JSON line {"result": "success"|"rejected"|"aborted"|"failed",
                             "auth_name": "<name>"|""}

All diagnostic prints (from FaceVerifier etc.) are redirected to stderr so
they never corrupt the stdout JSON channel.
"""

import sys
import os
import json


def main():
    # ── 1. Read config from parent ────────────────────────────────────────────
    raw = sys.stdin.readline()
    if not raw.strip():
        _send({"result": "failed", "auth_name": ""})
        return

    try:
        config = json.loads(raw)
    except Exception:
        _send({"result": "failed", "auth_name": ""})
        return

    project_root = config.get("project_root", "")
    env_path     = config.get("env_path", "")

    # ── 2. Make VisionSight modules importable ────────────────────────────────
    if project_root and project_root not in sys.path:
        sys.path.insert(0, project_root)

    # ── 3. Silence all prints to stdout so JSON channel stays clean ───────────
    _real_stdout = sys.stdout
    sys.stdout = sys.stderr          # all print() in FaceVerifier → stderr

    # ── 4. Load environment settings ─────────────────────────────────────────
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)

    # ── 5. Import heavy deps HERE — they live only in this process ────────────
    #       When this process exits, the OS reclaims all dlib / cv2 memory.
    from face_auth.verify import FaceVerifier
    from system.lock import SystemController

    # ── 6. Run the scan ───────────────────────────────────────────────────────
    system   = SystemController()
    verifier = FaceVerifier(headless=True)
    result   = "failed"

    try:
        result = verifier.authenticate_once(
            system,
            use_esc_hook=False,
            defer_unlock=True,   # parent process handles the actual unlock
        )
    except Exception as e:
        print(f"[scan_worker] exception during scan: {e}", file=sys.stderr)
        result = "failed"

    auth_name = ""
    if result == "success" and verifier.AUTO_UNLOCK:
        auth_name = verifier.auth_name or ""

    # ── 7. Restore stdout and send result ────────────────────────────────────
    sys.stdout = _real_stdout
    _send({"result": result, "auth_name": auth_name})
    # Process exits here → OS reclaims all dlib / cv2 / numpy / face_recognition
    # memory. Parent tray process stays at its ~84 MB private-memory baseline.


def _send(data: dict):
    print(json.dumps(data), flush=True)


if __name__ == "__main__":
    main()
