# system/lock.py
import os
import subprocess
import time
import Quartz

class SystemController:
    def __init__(self):
        self.last_lock_time = 0
        self.LOCK_COOLDOWN = 0
        self.last_unlock_time = 0

    def _get_secure_password(self):
        try:
            output = subprocess.check_output(
                ['security', 'find-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w'],
                text=True
            ).strip()
            return output
        except subprocess.CalledProcessError:
            print('ERROR: Password not found in Keychain!')
            return None

    def _is_display_on(self):
        try:
            intel_res = subprocess.run(
                'ioreg -n IODisplayWrangler | grep -i IOPowerManagement',
                shell=True, capture_output=True, text=True
            ).stdout
            if 'CurrentPowerState' in intel_res:
                return ('"CurrentPowerState"=4' in intel_res) or ('"CurrentPowerState"= 4' in intel_res)
            m_res = subprocess.run(
                'ioreg -c IOMobileFramebuffer -r -l | grep "DisplayPowerState"',
                shell=True, capture_output=True, text=True
            ).stdout
            if 'DisplayPowerState' in m_res:
                return '1' in m_res
            return True
        except Exception:
            return True

    def _is_macos_locked(self):
        try:
            session = Quartz.CGSessionCopyCurrentDictionary()
            if session is None:
                return False
                
            screen_locked = session.get('CGSSessionScreenIsLocked', None)
            lock_time = session.get('CGSSessionScreenLockedTime', None)
            
            if screen_locked is None or lock_time is None:
                return False
                
            if not screen_locked:
                return False
                
            return True
        except Exception as e:
            print(f'Lock State Error: {e}')
            return False

    def lock_mac(self, reason='Security Trigger'):
        current_time = time.time()
        if current_time - self.last_lock_time < self.LOCK_COOLDOWN:
            return False
        try:
            subprocess.run([
                '/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession',
                '-suspend'
            ], check=True)
            self.last_lock_time = current_time
            return True
        except Exception as e:
            print(f'Lock failed: {e}')
            return False

    def simulate_unlock(self, user_name):
        if self._is_macos_locked():
            print(f'Access Granted to {user_name}. Waking Mac...')
            try:
                # Run caffeinate in the background so it doesn't block for 2 seconds
                subprocess.Popen(['caffeinate', '-u', '-t', '2'])
                mac_password = self._get_secure_password()
                if mac_password:
                    # CRITICAL: Use kCGEventSourceStatePrivate so WindowServer
                    # accepts HID events from an LSUIElement / ad-hoc signed app.
                    # Using None (kCGEventSourceStateHIDSystemState) is silently
                    # rejected by macOS Sonoma+ for non-frontmost processes.
                    source = Quartz.CGEventSourceCreate(
                        Quartz.kCGEventSourceStatePrivate
                    )

                    # Wake screen via Spacebar
                    space_down = Quartz.CGEventCreateKeyboardEvent(source, 49, True)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, space_down)
                    space_up = Quartz.CGEventCreateKeyboardEvent(source, 49, False)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, space_up)
                    
                    # Sonoma's lock screen takes longer to render the password
                    # field — 0.3s is too fast, 0.8s is reliable.
                    time.sleep(0.8)
                    
                    # Type password at HID level — kCGHIDEventTap is the ONLY tap
                    # that works at the lock screen. kCGSessionEventTap is silently
                    # blocked by macOS when the session is locked.
                    for char in mac_password:
                        uni_char = ord(char)
                        event_down = Quartz.CGEventCreateKeyboardEvent(source, 0, True)
                        Quartz.CGEventKeyboardSetUnicodeString(event_down, 1, chr(uni_char))
                        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
                        time.sleep(0.03)
                        event_up = Quartz.CGEventCreateKeyboardEvent(source, 0, False)
                        Quartz.CGEventKeyboardSetUnicodeString(event_up, 1, chr(uni_char))
                        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
                        time.sleep(0.03)  # 30ms inter-char delay for HID reliability
                        
                    # Small gap before Enter so the password field processes
                    # the last character before submission
                    time.sleep(0.1)

                    # Press Enter to login
                    enter_down = Quartz.CGEventCreateKeyboardEvent(source, 36, True)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, enter_down)
                    enter_up = Quartz.CGEventCreateKeyboardEvent(source, 36, False)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, enter_up)

                    print('Unlock sequence complete!')
                else:
                    print('⚠️ No password in Keychain — cannot unlock.')
            except Exception as e:
                print(f'Unlock error: {e}')
            self.last_unlock_time = time.time()
        return True
