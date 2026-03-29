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
                subprocess.run(['caffeinate', '-u', '-t', '2'], check=True)
                mac_password = self._get_secure_password()
                if mac_password:
                    # Wake screen via Spacebar
                    space_down = Quartz.CGEventCreateKeyboardEvent(None, 49, True)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, space_down)
                    space_up = Quartz.CGEventCreateKeyboardEvent(None, 49, False)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, space_up)
                    
                    time.sleep(0.15) # Wait a tiny fraction of a second for UI to wake up
                    
                    # Instantly type the password using C-level Unicode keyboard events
                    for char in mac_password:
                        uni_char = ord(char)
                        event_down = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
                        Quartz.CGEventKeyboardSetUnicodeString(event_down, 1, chr(uni_char))
                        Quartz.CGEventPost(Quartz.kCGSessionEventTap, event_down)
                        event_up = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
                        Quartz.CGEventKeyboardSetUnicodeString(event_up, 1, chr(uni_char))
                        Quartz.CGEventPost(Quartz.kCGSessionEventTap, event_up)
                        
                    # Press Enter to login
                    enter_down = Quartz.CGEventCreateKeyboardEvent(None, 36, True)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, enter_down)
                    enter_up = Quartz.CGEventCreateKeyboardEvent(None, 36, False)
                    Quartz.CGEventPost(Quartz.kCGHIDEventTap, enter_up)

                    print('Unlock sequence complete!')
            except Exception as e:
                print(f'Unlock error: {e}')
            self.last_unlock_time = time.time()
        return True
