import time
from system.lock import SystemController
from face_auth.verify import FaceVerifier

def start_daemon():
    print("==================================================")
    print("🚀 VISIONSIGHT OS SECURITY DAEMON (IDLE MODE)")
    print("==================================================")
    
    # Initialize Core Modules
    system = SystemController()
    verifier = FaceVerifier(headless=False)
    
    print("✅ System Ready. Entering 0% CPU Sleep State...")

    while True:
        try:
            # Sleep aggressively to prevent CPU usage
            time.sleep(1)
            
            # Check Physical State (Issue #4 & Issue #10)
            is_locked = system._is_macos_locked()
            is_awake = system._is_display_on()
            
            if is_locked and is_awake:
                print("\n🔔 [EVENT] Lock Screen Detected & Display is ON!")
                
                # Check Cooldown to prevent Continuous Lock-Unlock Loop
                current_time = time.time()
                if current_time - system.last_unlock_time < system.LOCK_COOLDOWN:
                    remaining = int(system.LOCK_COOLDOWN - (current_time - system.last_unlock_time))
                    print(f"⏳ Cooldown Active ({remaining}s remaining). Waiting for you to leave...")
                    continue
                
                # Hand over control to the biometric authenticator
                verifier.authenticate_once(system)
                
                # Once authenticate_once returns, the process either succeeded, failed, or the screen turned off.
                # It safely returns to the IDLE sleep loop.
                print("💤 Biometric Session Closed. Returning to IDLE sleep...")

        except KeyboardInterrupt:
            print("\n🛑 Shutting down VisionSight Daemon.")
            break
        except Exception as e:
            print(f"⚠️ Daemon Error: {e}")
            time.sleep(5)  # Prevent crash looping

if __name__ == "__main__":
    start_daemon()
