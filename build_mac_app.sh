#!/bin/bash
# build_mac_app.sh — VisionSight Single-Binary DMG Builder v3
# -----------------------------------------------------------
# GUI and Daemon are now the SAME process (daemon runs as a
# background thread). No VisionSightDaemon binary is needed.
set -e

echo "===================================="
echo "🍏 VISIONSIGHT DMG BUILDER v3 🍏"
echo "===================================="

# ── Clean previous builds ─────────────────────────────────────────────────────
echo "🧹 Cleaning previous builds..."
hdiutil detach /Volumes/VisionSight -force 2>/dev/null || true
sudo rm -rf build dist
mkdir -p build

# ── Build single binary with PyInstaller ─────────────────────────────────────
echo "[1/3] Building with PyInstaller (single binary)..."
pyinstaller --noconfirm VisionSight.spec

APP="dist/VisionSight.app"

# ── Patch Info.plist entitlements (belt-and-suspenders) ──────────────────────
echo "[2/3] Patching Info.plist entitlements..."

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

# ── Remove metadata dirs that break codesign ─────────────────────────────────
find "$APP" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find "$APP" -name "*.data"      -type d -exec rm -rf {} + 2>/dev/null || true
xattr -cr "$APP" 2>/dev/null || true

# ── Ad-hoc sign all binaries ──────────────────────────────────────────────────
echo "🔏 Signing dylibs and .so files..."
find "$APP" -name "*.dylib" -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP" -name "*.so"    -exec codesign --force --sign - {} \; 2>/dev/null || true
find "$APP" -type f | while read f; do
    if file "$f" | grep -q "Mach-O"; then
        codesign --force --sign - "$f" 2>/dev/null || true
    fi
done

echo "✍️  Signing App Bundle..."
codesign --force --sign - --timestamp=none --no-strict "$APP" \
    && echo "✅ Bundle signed!" \
    || echo "⚠️  Signing warning — continuing anyway"

# ── Embed uninstall helper ────────────────────────────────────────────────────
cat > "$APP/Contents/Resources/uninstall.sh" << 'EOF'
#!/bin/bash
# VisionSight Uninstaller
# The daemon is now an in-process thread; no launchd plist needed.
# But we clean up any legacy plist from v4.x installs just in case.
launchctl unload ~/Library/LaunchAgents/com.visionsight.daemon.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.visionsight.daemon.plist
rm -rf ~/Library/Application\ Support/VisionSight
rm -rf /Applications/VisionSight.app
security delete-generic-password -a "$(whoami)" -s VisionSightDaemon 2>/dev/null || true
echo "✅ VisionSight uninstalled."
EOF
chmod +x "$APP/Contents/Resources/uninstall.sh"

# ── Create DMG ────────────────────────────────────────────────────────────────
echo "[3/3] Creating DMG..."
mkdir -p dist/dmg_staging
cp -R "$APP" dist/dmg_staging/
ln -sf /Applications dist/dmg_staging/Applications
hdiutil create \
    -volname VisionSight \
    -srcfolder dist/dmg_staging \
    -ov -format UDZO \
    dist/VisionSight.dmg \
    && echo "✅ DMG created!"

# ── Post-install helper ───────────────────────────────────────────────────────
cat > dist/install_helper.sh << 'EOF'
#!/bin/bash
echo "🔧 Configuring VisionSight..."
sudo xattr -rd com.apple.quarantine /Applications/VisionSight.app 2>/dev/null || true
sudo spctl --add /Applications/VisionSight.app 2>/dev/null || true
echo "✅ Done! Open VisionSight from Applications."
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