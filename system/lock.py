import os
import subprocess
import time

class SystemController:
    def __init__(self):
        self.last_lock_time = 0
        self.LOCK_COOLDOWN = 0  # Cooldown completely removed so you can unlock infinitely without waiting
        self.last_unlock_time = 0

    def _get_secure_password(self):
        """
        Dynamically extracts the user's password from Apple's highly-encrypted local Keychain securely at runtime.
        """
        try:
            output = subprocess.check_output(
                ['security', 'find-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w'], 
                text=True
            ).strip()
            return output
        except subprocess.CalledProcessError:
            print("⚠️ ERROR: Password not found in Keychain! Have you run the 'security add-generic-password' setup command?")
            return None

    def _is_display_on(self):
        """
        Queries the macOS Display hardware kernel directly to check if the backlight is powered on.
        If CurrentPowerState is 1, 2, or 3, the display is asleep/blank. If 4, the screen is brightly awake.
        Silently falls back to True for newer Apple Silicon Macs that use a different registry key.
        """
        try:
            # check_output throws an exception if grep returns 1 (no match found).
            # subprocess.run with capture_output is safer here so we don't spam the console.
            result = subprocess.run('ioreg -n IODisplayWrangler | grep -i IOPowerManagement', shell=True, capture_output=True, text=True)
            output = result.stdout
            if "CurrentPowerState" in output:
                return ('"CurrentPowerState"=4' in output) or ('"CurrentPowerState"= 4' in output)
            return True # Fallback for Apple Silicon architecture
        except Exception:
            return True

    def _is_macos_locked(self):
        """
        Dynamically queries the underlying macOS kernel using Apple's I/O Kit registry 
        to perfectly determine if the user is currently trapped on the Lock Screen.
        Returns True if locked, False if the desktop is already open.
        """
        try:
            # ioreg natively exposes the CoreGraphics session state (CGSSession)
            # If the screen is locked, this key is physically injected into the registry.
            output = subprocess.check_output('ioreg -n Root -d1 -a', shell=True).decode()
            return "CGSSessionScreenIsLocked" in output
        except Exception as e:
            print(f"⚠️ Lock State Check Error: {e}")
            return False

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
            self.last_lock_time = current_time
            
            # Phase 5 hook placeholder: we will log this event later.
            return True
        except Exception as e:
            print(f"❌ SystemController Error: Failed to execute macOS lock - {e}")
            return False

    def simulate_unlock(self, user_name):
        """
        Simulates unlocking the system. 
        Hooks into the dynamic macOS Lock state to decide whether to type the password.
        """
        current_time = time.time()
        
        if self._is_macos_locked():
            print(f"🔓 SystemController: Mac is Locked! Access Granted to '{user_name}'. Waking Mac up...")
            
            # Wakes up the physical display by simulating user activity for 2 seconds
            try:
                subprocess.run(["caffeinate", "-u", "-t", "2"], check=True)
                
                # Retrieve exact password from Apple Keychain dynamically
                mac_password = self._get_secure_password()
                
                if mac_password:
                    # Give the physical screen a tiny fraction of a second to power on
                    time.sleep(0.2)
                    print("🤖 Injecting HIGH SPEED keychain payload to bypass lock screen...")

                    # AppleScript to simulate keyboard events (Requires macOS Accessibility permissions)
                    apple_script = f'''
                    tell application "System Events"
                        # 1. Press Spacebar to wake the actual password prompt box
                        key code 49
                        delay 0.1
                        
                        # 2. Type the password into the box
                        keystroke "{mac_password}"
                        
                        # 3. Press Enter instantly
                        key code 36
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", apple_script], check=True)
                    print("✅ macOS Lock Screen successfully bypassed!")

            except Exception as e:
                print(f"⚠️ Could not complete AppleScript bypass: {e}")

            self.last_unlock_time = current_time
        else:
            print(f"👁️‍🗨️ Biometrics Authenticated '{user_name}' (Bypass Ignored: Mac is already awake).")
            
        return True
