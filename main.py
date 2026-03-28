from face_auth.verify import FaceVerifier
from system.lock import SystemController

def start_vision_sight():
    print("=" * 50)
    print("🚀 INITIALIZING VISIONSIGHT OS SECURITY SYSTEM")
    print("=" * 50)

    # 1. Initialize macOS System Controller
    sys_controller = SystemController()

    # Define Callback Functions for the FaceVerifier
    def handle_lock(reason):
        sys_controller.lock_mac(reason=reason)

    def handle_unlock(user_name):
        sys_controller.simulate_unlock(user_name=user_name)

    # 2. Initialize the Biometric Verifier with Callbacks & Headless Mode
    try:
        verifier = FaceVerifier(
            on_lock=handle_lock, 
            on_unlock=handle_unlock,
            headless=False  # Set to False so the user can actually see it working!
        )
        
        # 3. Start the continuous monitoring loop
        verifier.run()

    except Exception as e:
        print(f"❌ Critical System Failure: {e}")
        print("Ensuring system is secured before exiting...")
        sys_controller.lock_mac(reason="Fatal Error / Crash")

if __name__ == "__main__":
    start_vision_sight()
