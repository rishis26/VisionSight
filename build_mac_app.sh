#!/bin/bash
set -e

echo "===================================="
echo "🍏 VISIONSIGHT DMG BUILDER v2 🍏"
echo "===================================="

echo "🧹 Cleaning previous builds..."
hdiutil detach /Volumes/VisionSight -force 2>/dev/null || true
pkill -f VisionSightDaemon 2>/dev/null || true
sudo rm -rf build dist
mkdir -p build

echo "[1/4] Building with PyInstaller spec..."
pyinstaller --noconfirm VisionSight.spec

echo "[2/4] Integrating Daemon into App Bundle..."
APP="dist/VisionSight.app"

cp -Rf dist/VisionSightDaemon/* "$APP/Contents/MacOS/"
chmod +x "$APP/Contents/MacOS/VisionSightDaemon"

plutil -insert NSCameraUsageDescription \
    -string "VisionSight requires camera access for biometric face authentication." \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace NSCameraUsageDescription \
    -string "VisionSight requires camera access for biometric face authentication." \
    "$APP/Contents/Info.plist"

plutil -insert NSAppleEventsUsageDescription \
    -string "VisionSight needs to control keyboard events to unlock your Mac." \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace NSAppleEventsUsageDescription \
    -string "VisionSight needs to control keyboard events to unlock your Mac." \
    "$APP/Contents/Info.plist"

# Remove metadata dirs that break codesign
find "$APP" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find "$APP" -name "*.data" -type d -exec rm -rf {} + 2>/dev/null || true

xattr -cr "$APP" 2>/dev/null || true

echo "🔏 Signing binaries..."
find "$APP" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP" -name "*.so" -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP" -type f | while read f; do
    if file "$f" | grep -q "Mach-O"; then
        codesign --force --sign - "$f" 2>/dev/null || true
    fi
done

echo "✍️  Signing App Bundle..."
codesign --force --sign - --timestamp=none --no-strict "$APP" \
    && echo "✅ Bundle signed!" \
    || echo "⚠️  Signing warning — continuing anyway"

cat > "$APP/Contents/Resources/uninstall.sh" << 'EOF'
#!/bin/bash
launchctl unload ~/Library/LaunchAgents/com.visionsight.daemon.plist 2>/dev/null || true
rm -rf ~/Library/Application\ Support/VisionSight
rm -f ~/Library/LaunchAgents/com.visionsight.daemon.plist
rm -rf /Applications/VisionSight.app
security delete-generic-password -a $(whoami) -s VisionSightDaemon 2>/dev/null || true
echo "VisionSight uninstalled."
EOF
chmod +x "$APP/Contents/Resources/uninstall.sh"

echo "[3/4] Creating DMG..."
mkdir -p dist/dmg_staging
cp -R "$APP" dist/dmg_staging/
ln -sf /Applications dist/dmg_staging/Applications
hdiutil create -volname VisionSight -srcfolder dist/dmg_staging -ov -format UDZO dist/VisionSight.dmg \
    && echo "✅ DMG created!"

echo "[4/4] Creating install helper for target Macs..."
cat > dist/install_helper.sh << 'EOF'
#!/bin/bash
echo "Configuring VisionSight..."
sudo xattr -rd com.apple.quarantine /Applications/VisionSight.app 2>/dev/null || true
sudo spctl --add /Applications/VisionSight.app 2>/dev/null || true
echo "Done! Open VisionSight from Applications."
EOF
chmod +x dist/install_helper.sh

echo ""
echo "===================================="
echo "✅ BUILD COMPLETE!"
echo "===================================="
echo "💿 DMG:            dist/VisionSight.dmg"
echo "🔧 Install helper: dist/install_helper.sh"
echo ""
echo "On target Mac — after dragging to Applications:"
echo "  Open Terminal and run: bash install_helper.sh"
echo "===================================="