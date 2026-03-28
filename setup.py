import os
import subprocess
import getpass

def setup_keychain():
    print("====================================")
    print(" 🔐 VISIONSIGHT KEYCHAIN SETUP")
    print("====================================")
    print("To bypass the macOS Lock Screen, the Auto-Typer needs your Mac password.")
    print("This will securely encrypt it into the hardware Apple Keychain.")

    mac_password = getpass.getpass("Enter your Mac Login Password (typing is hidden): ")
    
    if not mac_password:
        print("Password cannot be empty!")
        return
        
    try:
        # We delete any old corrupted key first just in case
        subprocess.run(['security', 'delete-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon'], 
                       capture_output=True)
                       
        # Inject the new password
        subprocess.run(['security', 'add-generic-password', '-a', os.getlogin(), '-s', 'VisionSightDaemon', '-w', mac_password], 
                       check=True)
        print("\n✅ SUCCESS! Your password is now securely encrypted in the macOS Keychain!")
        print("You can now securely run: python3 main.py")
    except Exception as e:
        print(f"\n⚠️ FAILED to write to Keychain: {e}")

if __name__ == "__main__":
    setup_keychain()
