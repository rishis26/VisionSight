import os
import subprocess
import time
from dotenv import load_dotenv

# Load secure environment variables
load_dotenv()
MAC_PASSWORD = os.getenv("MAC_PASSWORD")

if not MAC_PASSWORD:
    print("⚠️ WARNING: MAC_PASSWORD not found in .env file! True Face ID Auto-Typer is disabled.")


class SystemController:
    def __init__(self):
        self.is_locked = False
        self.last_lock_time = 0
        self.LOCK_COOLDOWN = 10  # Minimum seconds between lock commands to prevent spamming
        self.last_unlock_time = 0

    def lock_mac(self, reason="Security Trigger"):
        """
        Executes the macOS screen lock command.
        Command used: 'pmset displaysleepnow' forces the screen to sleep and requires a password on wake 
        (if 'Require password immediately after sleep' is enabled in macOS settings).
        """
        current_time = time.time()
        
        # Debounce/Grace Period: prevent spamming the lock command rapidly
        if current_time - self.last_lock_time < self.LOCK_COOLDOWN:
            print(f"🔒 SystemController: Ignoring lock request (Cooldown active for {int(self.LOCK_COOLDOWN - (current_time - self.last_lock_time))}s).")
            return False

        print(f"🔒 SystemController: SECURING MAC... Reason: {reason}.")
        try:
            # Force Display Sleep (Actual macOS Hardware Lock)
            print("🛑 [ACTUAL LOCK ACTIVATED] -> Executing pmset displaysleepnow...")
            subprocess.run(["pmset", "displaysleepnow"], check=True)
            self.is_locked = True
            self.last_lock_time = current_time
            
            # Phase 5 hook placeholder: we will log this event later.
            return True
        except Exception as e:
            print(f"❌ SystemController Error: Failed to execute macOS lock - {e}")
            return False

    def simulate_unlock(self, user_name):
        """
        Simulates unlocking the system. 
        Note: macOS does not allow a clean programmatic unlock past the login screen without inserting passwords, 
        so we register this as 'Access Granted' in our internal state.
        """
        current_time = time.time()
        if self.is_locked:
            print(f"🔓 SystemController: Access Granted to '{user_name}'. Waking Mac up...")
            
            # Wakes up the physical display by simulating user activity for 2 seconds
            try:
                subprocess.run(["caffeinate", "-u", "-t", "2"], check=True)
                
                # The True Face ID Auto-Typer bypass logic
                if MAC_PASSWORD:
                    # Wait briefly to ensure the physical screen is on and the login prompt is ready
                    time.sleep(1.0)
                    print("🤖 Injecting secure payload to bypass lock screen...")

                    # AppleScript to simulate keyboard events (Requires macOS Accessibility permissions)
                    apple_script = f'''
                    tell application "System Events"
                        # 1. Press Spacebar to wake the actual password prompt box
                        key code 49
                        delay 1.0
                        
                        # 2. Type the password into the box
                        keystroke "{MAC_PASSWORD}"
                        delay 0.2
                        
                        # 3. Press Enter
                        key code 36
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", apple_script], check=True)
                    print("✅ macOS Lock Screen successfully bypassed!")

            except Exception as e:
                print(f"⚠️ Could not complete AppleScript bypass: {e}")

            self.is_locked = False
            self.last_unlock_time = current_time
        return True
