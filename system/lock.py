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
        """
        Unlock the Mac lock screen by typing the stored password.

        On Sonoma, CGEventPost(kCGHIDEventTap) is silently filtered for
        LSUIElement (background-only) apps. The fix: temporarily switch
        the activation policy to Regular (foreground) before posting
        events, then switch back to Accessory after. This makes
        WindowServer reclassify the process as foreground-capable.
        """
        if not self._is_macos_locked():
            return True

        print(f'Access Granted to {user_name}. Waking Mac...')
        try:
            mac_password = self._get_secure_password()
            if not mac_password:
                print('⚠️ No password in Keychain — cannot unlock.')
                return False

            # Keep display awake for the entire unlock sequence
            subprocess.Popen(['caffeinate', '-u', '-t', '5'])

            import sys
            is_bundled = getattr(sys, 'frozen', False)

            if is_bundled:
                print('📦 [BUNDLED] Switching to foreground policy for HID injection...')
                try:
                    from AppKit import (
                        NSApplication,
                        NSApplicationActivationPolicyRegular,
                        NSApplicationActivationPolicyAccessory
                    )
                    ns_app = NSApplication.sharedApplication()
                    # Switch to foreground — allows CGEventPost through
                    ns_app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
                    print('🔄 Activation policy → Regular (foreground)')
                    time.sleep(0.1)  # Let WindowServer process the change

                    success = self._inject_direct(mac_password)

                    # Switch back to background (tray-only)
                    ns_app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
                    print('🔄 Activation policy → Accessory (background)')
                except Exception as e:
                    print(f'⚠️ Policy switch failed: {e} — trying direct anyway')
                    success = self._inject_direct(mac_password)
            else:
                print('🐍 [DEV] Using direct CGEventPost...')
                success = self._inject_direct(mac_password)

            if success:
                print('✅ Unlock sequence dispatched.')
            else:
                print('⚠️ Unlock sequence may have failed.')

            self.last_unlock_time = time.time()
            return success

        except Exception as e:
            print(f'Unlock error: {e}')
            self.last_unlock_time = time.time()
            return False

    # ── Bundled mode: osascript bridge ────────────────────────────────────

    @staticmethod
    def _escape_for_applescript(s):
        """Escape a string for safe embedding inside AppleScript double quotes.

        AppleScript string literals use " as delimiter and \\ as escape.
        Characters that must be escaped:   \\ → \\\\    \" → \\"
        All other characters (including ', spaces, !, @, etc.) are safe
        inside AppleScript double-quoted strings without escaping.
        """
        return s.replace('\\', '\\\\').replace('"', '\\"')

    def _inject_via_helper(self, password):
        """
        Run the compiled unlock_helper binary to type the password.

        unlock_helper is a tiny C binary (NOT LSUIElement) that calls
        CGEventPost(kCGHIDEventTap) natively. WindowServer allows its
        HID events through to loginwindow because it's classified as a
        foreground-capable process.

        Password is piped via stdin — never in the process list.

        The binary is bundled at Contents/MacOS/unlock_helper in the .app.
        """
        import sys

        # Find the helper binary next to the main executable
        helper_path = os.path.join(os.path.dirname(sys.executable), 'unlock_helper')

        if not os.path.exists(helper_path):
            # Fallback: check project directory (dev builds)
            helper_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'unlock_helper'
            )

        if not os.path.exists(helper_path):
            print(f'⚠️ unlock_helper not found — falling back to direct CGEventPost')
            return self._inject_direct(password)

        try:
            result = subprocess.run(
                [helper_path],
                input=password + '\n',
                capture_output=True,
                text=True,
                timeout=12,
            )
            if result.returncode == 0:
                return True

            stderr = result.stderr.strip()
            print(f'⚠️ unlock_helper error (rc={result.returncode}): {stderr}')
            print('🔄 Falling back to direct CGEventPost...')
            return self._inject_direct(password)

        except subprocess.TimeoutExpired:
            print('⚠️ unlock_helper timed out (12s)')
            return False
        except PermissionError:
            print('⚠️ unlock_helper not executable — falling back')
            return self._inject_direct(password)

    # ── Dev mode: direct CGEventPost ─────────────────────────────────────

    def _inject_direct(self, password):
        """
        Direct CGEventPost — works from non-LSUIElement processes only.
        Used in dev mode (python3 gui/app.py) and as a last-resort fallback.
        """
        source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStatePrivate)
        tap = Quartz.kCGHIDEventTap

        # Spacebar wake
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(source, 49, down)
            Quartz.CGEventPost(tap, ev)

        time.sleep(0.8)

        # Type password
        for char in password:
            for down in (True, False):
                ev = Quartz.CGEventCreateKeyboardEvent(source, 0, down)
                Quartz.CGEventKeyboardSetUnicodeString(ev, 1, char)
                Quartz.CGEventPost(tap, ev)
                time.sleep(0.02)

        time.sleep(0.05)

        # Enter
        for down in (True, False):
            ev = Quartz.CGEventCreateKeyboardEvent(source, 36, down)
            Quartz.CGEventPost(tap, ev)

        return True

