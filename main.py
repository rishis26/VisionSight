import time
from system.lock import SystemController
from face_auth.verify import FaceVerifier

def start_daemon():
    print("==================================================")
    print("🚀 VISIONSIGHT OS SECURITY DAEMON (IDLE MODE)")
    print("==================================================")
    
    system = SystemController()
    verifier = FaceVerifier(headless=True)
    
    print("✅ System Ready. Entering 0% CPU Sleep State...")

    while True:
        try:
            time.sleep(0.2)

            # GATE: Only fire if screen is genuinely locked
            if not system._is_macos_locked():
                continue

            print("\n🔔 [EVENT] Real Lock Screen confirmed! Starting biometric scan...")

            # Hand over to face scanner — get back a clear result
            result = verifier.authenticate_once(system)

            # ── RESULT HANDLING ──────────────────────────────────────────────

            if result == "success":
                # Face matched and unlocked — wait for macOS to fully wake
                # before polling again to avoid the re-lock loop
                print("✅ Unlock successful. Cooling down for 5 seconds...")
                time.sleep(5)

            elif result == "rejected":
                # User pressed Esc — they want to type password manually
                # Wait here doing nothing until they successfully unlock themselves
                print("⌨️  Manual unlock mode. Waiting for user to type password...")
                while system._is_macos_locked():
                    time.sleep(0.5)
                # Screen is now unlocked — give it a moment to settle
                print("✅ Manual unlock detected. Resuming daemon...")
                time.sleep(3)

            elif result == "aborted":
                # Screen unlocked by some other means mid-scan
                # Just give it a moment and go back to polling
                print("↩️  Scan aborted. Resuming idle...")
                time.sleep(2)

            elif result == "failed":
                # Camera error — wait a bit before retrying
                print("⚠️  Camera failed. Retrying in 5 seconds...")
                time.sleep(5)

            # ─────────────────────────────────────────────────────────────────
            print("💤 Returning to IDLE...")

        except KeyboardInterrupt:
            print("\n🛑 Shutting down VisionSight Daemon.")
            break
        except Exception as e:
            print(f"⚠️ Daemon Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_daemon()