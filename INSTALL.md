# VisionSight Installation Guide

## System Requirements

- macOS 11.0 (Big Sur) or later
- Apple Silicon (M1/M2/M3) or Intel Mac
- Built-in or external webcam
- Python 3.8+ (for development builds)

## Installation Methods

### Method 1: DMG Installer (Recommended for End Users)

1. Download `VisionSight.dmg`
2. Double-click to mount the DMG
3. Drag `VisionSight.app` to the `Applications` folder
4. Eject the DMG
5. Launch VisionSight from Applications

### Method 2: From Source (For Developers)

```bash
# Clone the repository
git clone https://github.com/yourusername/visionsight.git
cd visionsight

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pyinstaller dmgbuild

# Build the DMG
chmod +x build_mac_app.sh
./build_mac_app.sh

# The DMG will be created at: dist/VisionSight.dmg
```

## First Launch Setup

When you first launch VisionSight, you'll need to:

### 1. Grant Camera Permission
- macOS will prompt you to allow camera access
- Click "OK" to grant permission
- If denied, go to System Settings → Privacy & Security → Camera

### 2. Grant Accessibility Permission
- Required for auto-typing your password
- Go to System Settings → Privacy & Security → Accessibility
- Click the lock icon and authenticate
- Enable VisionSight

### 3. Store Password in Keychain
- The app will prompt you to enter your Mac login password
- This is stored securely in macOS Keychain (encrypted)
- Never stored in plain text

### 4. Register Your Face
- Click "Capture Face" in the app
- Position your face in the camera view
- The app will save your face encoding

### 5. Start the Daemon
- Click "Start Daemon" to enable auto-unlock
- The daemon runs in the background at 0% CPU
- Lock your Mac to test it

## Permissions Troubleshooting

### Camera Not Working
```bash
# Reset camera permissions
tccutil reset Camera com.visionsight.app
```

### Accessibility Not Working
1. System Settings → Privacy & Security → Accessibility
2. Remove VisionSight from the list
3. Re-add it by clicking the "+" button
4. Navigate to `/Applications/VisionSight.app`

### Password Not Unlocking
```bash
# Re-run the keychain setup
python3 setup.py
```

## Configuration

Edit `~/.visionsight/.env` to customize:

```bash
# Camera settings
VISIONSIGHT_CAMERA=0                    # Camera index (0 = default)
VISIONSIGHT_TOLERANCE=0.45              # Face match threshold (lower = stricter)
VISIONSIGHT_AUTO_UNLOCK=true            # Auto-type password on match

# Timing settings
VISIONSIGHT_ACTIVATION_WINDOW=4         # Seconds to scan for face
VISIONSIGHT_COOLDOWN=10                 # Seconds between scans
VISIONSIGHT_IDLE_THRESHOLD=4            # Seconds before idle timeout

# Performance settings
VISIONSIGHT_FPS=Medium                  # Low/Medium/High
VISIONSIGHT_RESOLUTION=640x480          # 640x480 or 1280x720
```

## Uninstallation

### Method 1: Using Uninstaller Script
```bash
/Applications/VisionSight.app/Contents/Resources/uninstall.sh
```

### Method 2: Manual Removal
```bash
# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.visionsight.daemon.plist

# Remove files
rm -rf /Applications/VisionSight.app
rm -rf ~/Library/Application\ Support/VisionSight
rm -f ~/Library/LaunchAgents/com.visionsight.daemon.plist

# Remove keychain entry
security delete-generic-password -a $(whoami) -s VisionSightDaemon
```

## Security Notes

- Your password is stored in macOS Keychain with hardware encryption
- Face encodings are stored locally (never uploaded)
- The daemon requires Accessibility permissions to type your password
- Camera access is only used when the screen is locked
- All processing happens on-device

## Support

- Issues: https://github.com/yourusername/visionsight/issues
- Documentation: https://github.com/yourusername/visionsight/wiki
- Email: support@visionsight.app
