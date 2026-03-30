# VisionSight Build Guide

## Prerequisites

### Required Software
```bash
# Python 3.8 or later
python3 --version

# Pip packages
pip3 install pyinstaller dmgbuild

# Xcode Command Line Tools (for codesigning)
xcode-select --install
```

### Required Python Packages
```bash
pip3 install -r requirements.txt
```

## Build Process

### Quick Build
```bash
chmod +x build_mac_app.sh
./build_mac_app.sh
```

### Build Output
```
dist/
├── VisionSight.app          # Standalone macOS application
├── VisionSight.dmg          # Distributable installer
└── .installer/              # Installation instructions
```

## Build Steps Explained

### Step 1: Build Daemon
```bash
pyinstaller --noconfirm --onedir --paths . \
    --hidden-import system.paths \
    --hidden-import pynput \
    --collect-all objc \
    --collect-all Quartz \
    --collect-data face_recognition_models \
    -n VisionSightDaemon main.py
```

Creates the background daemon that monitors lock events.

### Step 2: Build GUI App
```bash
pyinstaller --noconfirm --windowed --paths . \
    --hidden-import system.paths \
    --icon=assets/icon.png \
    --add-data "assets:assets" \
    --collect-data face_recognition_models \
    -n VisionSight gui/app.py
```

Creates the GUI application for configuration and face registration.

### Step 3: Bundle Integration
```bash
# Merge daemon into app bundle
cp -Rf dist/VisionSightDaemon/* dist/VisionSight.app/Contents/MacOS/
chmod +x dist/VisionSight.app/Contents/MacOS/VisionSightDaemon
```

Integrates the daemon into the main app bundle.

### Step 4: Add Entitlements
```bash
# Camera permission
plutil -insert NSCameraUsageDescription -string "..." dist/VisionSight.app/Contents/Info.plist

# Accessibility permission
plutil -insert NSAppleEventsUsageDescription -string "..." dist/VisionSight.app/Contents/Info.plist
```

Adds required macOS permission descriptions.

### Step 5: Code Signing
```bash
codesign --force --deep --sign - dist/VisionSight.app
```

Signs the app bundle (use `-` for ad-hoc signing, or provide Developer ID).

### Step 6: Create DMG
```bash
dmgbuild -s dmg_settings.py "VisionSight" dist/VisionSight.dmg
```

Packages the app into a distributable DMG installer.

## Advanced Build Options

### Universal Binary (Apple Silicon + Intel)
```bash
# Build for both architectures
pyinstaller --target-arch universal2 ...
```

### Notarization (for Distribution)
```bash
# Sign with Developer ID
codesign --force --deep --sign "Developer ID Application: Your Name" dist/VisionSight.app

# Create signed DMG
hdiutil create -volname "VisionSight" -srcfolder dist/VisionSight.app -ov -format UDZO dist/VisionSight.dmg

# Notarize
xcrun notarytool submit dist/VisionSight.dmg --keychain-profile "AC_PASSWORD" --wait

# Staple notarization ticket
xcrun stapler staple dist/VisionSight.dmg
```

### Custom Icon
```bash
# Convert PNG to ICNS
mkdir VisionSight.iconset
sips -z 16 16     icon.png --out VisionSight.iconset/icon_16x16.png
sips -z 32 32     icon.png --out VisionSight.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out VisionSight.iconset/icon_32x32.png
sips -z 64 64     icon.png --out VisionSight.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out VisionSight.iconset/icon_128x128.png
sips -z 256 256   icon.png --out VisionSight.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out VisionSight.iconset/icon_256x256.png
sips -z 512 512   icon.png --out VisionSight.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out VisionSight.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out VisionSight.iconset/icon_512x512@2x.png
iconutil -c icns VisionSight.iconset
```

## Troubleshooting

### PyInstaller Errors
```bash
# Clear cache
rm -rf build dist __pycache__
pip3 install --upgrade pyinstaller

# Rebuild
./build_mac_app.sh
```

### Missing Dependencies
```bash
# Check hidden imports
pyinstaller --log-level DEBUG ...

# Add to spec file
hiddenimports=['missing_module']
```

### Code Signing Issues
```bash
# Check signature
codesign -vvv --deep --strict dist/VisionSight.app

# Re-sign
codesign --force --deep --sign - dist/VisionSight.app
```

### DMG Creation Fails
```bash
# Install dmgbuild
pip3 install dmgbuild

# Test manually
dmgbuild -s dmg_settings.py "VisionSight" test.dmg
```

## Build Optimization

### Reduce App Size
```bash
# Exclude unnecessary packages
--exclude-module matplotlib
--exclude-module pandas
--exclude-module scipy

# Use UPX compression
--upx-dir=/usr/local/bin
```

### Faster Builds
```bash
# Skip cleaning
# Comment out: rm -rf build dist

# Use cached builds
pyinstaller --noconfirm ...
```

## Distribution Checklist

- [ ] Test on clean macOS installation
- [ ] Verify camera permissions work
- [ ] Verify accessibility permissions work
- [ ] Test face registration
- [ ] Test auto-unlock functionality
- [ ] Check app size (should be < 500MB)
- [ ] Test DMG installation
- [ ] Test uninstaller script
- [ ] Update version number
- [ ] Create release notes
- [ ] Sign and notarize (for public distribution)

## Version Management

Update version in:
- `gui/app.py` (app version string)
- `dmg_settings.py` (DMG title)
- `README.md` (download links)
- Git tag: `git tag v1.0.0`
