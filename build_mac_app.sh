#!/bin/bash
# build_mac_app.sh — VisionSight Single-Binary DMG Builder v4
# -----------------------------------------------------------
# GUI and Daemon are now the SAME process (daemon runs as a
# background thread). No VisionSightDaemon binary is needed.
set -e

echo "===================================="
echo "🍏 VISIONSIGHT DMG BUILDER v4 🍏"
echo "===================================="

# ── Config ────────────────────────────────────────────────────────────────────
APP="dist/VisionSight.app"
ENTITLEMENTS="entitlements.plist"

# ── Clean previous builds ─────────────────────────────────────────────────────
echo "🧹 Cleaning previous builds..."
hdiutil detach /Volumes/VisionSight -force 2>/dev/null || true
sudo rm -rf build dist
mkdir -p build

# ── Compile unlock_helper (HID injection helper) ─────────────────────────────
echo "[1/6] Compiling unlock_helper..."
clang -O2 -o build/unlock_helper system/unlock_helper.c \
    -framework CoreGraphics -framework CoreFoundation \
    -arch arm64 \
    && echo "✅ unlock_helper compiled" \
    || { echo "❌ unlock_helper compilation failed!"; exit 1; }

# ── Build single binary with PyInstaller ─────────────────────────────────────
echo "[2/6] Building with PyInstaller (single binary)..."
pyinstaller --noconfirm VisionSight.spec

# ── Verify critical files exist in bundle ────────────────────────────────────
echo "[3/6] Verifying bundle contents..."

# Copy unlock_helper into the app bundle (next to the main executable)
cp build/unlock_helper "$APP/Contents/MacOS/unlock_helper"
chmod +x "$APP/Contents/MacOS/unlock_helper"
echo "✅ unlock_helper bundled at Contents/MacOS/unlock_helper"

# Check icon is bundled
if [ ! -f "$APP/Contents/Resources/icon.icns" ]; then
    echo "⚠️  icon.icns missing from bundle — copying..."
    cp assets/icon.icns "$APP/Contents/Resources/icon.icns"
fi

# Check face_recognition models are bundled
MODEL_COUNT=$(find "$APP" -name "*.dat" | wc -l | tr -d ' ')
if [ "$MODEL_COUNT" -lt 3 ]; then
    echo "❌ CRITICAL: Only $MODEL_COUNT .dat model files found in bundle!"
    echo "   Expected at least 3 (shape_predictor_68, shape_predictor_5, resnet_model)"
    echo "   The bundled app WILL crash on face recognition. Fix your spec!"
    # Don't exit — let the user investigate
else
    echo "✅ Found $MODEL_COUNT model .dat files in bundle"
fi

# Check assets/icon.png is bundled (needed for tray icon at runtime)
ICON_PNG=$(find "$APP" -path "*/assets/icon.png" | head -1)
if [ -z "$ICON_PNG" ]; then
    echo "⚠️  assets/icon.png missing from bundle — copying..."
    mkdir -p "$APP/Contents/MacOS/assets"
    cp assets/icon.png "$APP/Contents/MacOS/assets/icon.png"
fi

# ── Patch Info.plist (belt-and-suspenders) ───────────────────────────────────
echo "[4/6] Patching Info.plist..."

# Camera usage string
plutil -insert NSCameraUsageDescription \
    -string "VisionSight requires camera access for biometric face authentication." \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace NSCameraUsageDescription \
    -string "VisionSight requires camera access for biometric face authentication." \
    "$APP/Contents/Info.plist"

# Apple Events usage string
plutil -insert NSAppleEventsUsageDescription \
    -string "VisionSight needs to control keyboard events to unlock your Mac." \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace NSAppleEventsUsageDescription \
    -string "VisionSight needs to control keyboard events to unlock your Mac." \
    "$APP/Contents/Info.plist"

# Ensure LSUIElement is set (tray-only mode, no Dock icon)
plutil -insert LSUIElement \
    -bool true \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace LSUIElement \
    -bool true \
    "$APP/Contents/Info.plist"

# Ensure icon file reference
plutil -insert CFBundleIconFile \
    -string "icon" \
    "$APP/Contents/Info.plist" 2>/dev/null || \
plutil -replace CFBundleIconFile \
    -string "icon" \
    "$APP/Contents/Info.plist"

echo "✅ Info.plist patched"

# ── Remove metadata dirs that break codesign ─────────────────────────────────
find "$APP" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find "$APP" -name "*.data"      -type d -exec rm -rf {} + 2>/dev/null || true
find "$APP" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
xattr -cr "$APP" 2>/dev/null || true

# ── Ad-hoc sign all binaries ──────────────────────────────────────────────────
echo "[5/6] Code signing..."

echo "🔏 Signing dylibs and .so files..."
find "$APP" -name "*.dylib" -exec codesign --force --sign - --entitlements "$ENTITLEMENTS" {} \; 2>/dev/null || true
find "$APP" -name "*.so"    -exec codesign --force --sign - --entitlements "$ENTITLEMENTS" {} \; 2>/dev/null || true

# Sign all Mach-O binaries (except the main executable — signed separately below)
MAIN_EXE="$APP/Contents/MacOS/VisionSight"
find "$APP" -type f | while read f; do
    if [ "$f" = "$MAIN_EXE" ]; then
        continue  # Sign last with entitlements
    fi
    if file "$f" | grep -q "Mach-O"; then
        codesign --force --sign - --entitlements "$ENTITLEMENTS" "$f" 2>/dev/null || true
    fi
done

# CRITICAL: Sign the main executable EXPLICITLY with entitlements BEFORE the
# bundle-level sign. --deep only propagates the signing identity, NOT the
# entitlements. Without this, TCC/WindowServer won't see the camera or
# accessibility entitlements on the actual VisionSight binary.
echo "✍️  Signing main executable with entitlements..."
codesign --force --sign - --entitlements "$ENTITLEMENTS" --timestamp=none "$MAIN_EXE" \
    && echo "✅ Main executable signed with entitlements!" \
    || echo "⚠️  Main executable signing warning"

echo "✍️  Signing App Bundle..."
codesign --force --deep --sign - --entitlements "$ENTITLEMENTS" --timestamp=none --no-strict "$APP" \
    && echo "✅ Bundle signed!" \
    || echo "⚠️  Signing warning — continuing anyway"

# Verify signature
codesign --verify --verbose=2 "$APP" 2>&1 || echo "⚠️  Signature verification note (expected for ad-hoc)"

# Verify entitlements are actually embedded
echo "🔍 Verifying entitlements on main executable..."
codesign -d --entitlements - "$MAIN_EXE" 2>&1 | head -20

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
echo "[6/6] Creating DMG..."
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
cat > dist/install_helper.sh << 'INST_EOF'
#!/bin/bash
echo "🔧 Configuring VisionSight..."

# Remove quarantine attribute (blocks ad-hoc signed apps)
sudo xattr -rd com.apple.quarantine /Applications/VisionSight.app 2>/dev/null || true

# Add to Gatekeeper exceptions
sudo spctl --add /Applications/VisionSight.app 2>/dev/null || true

# Reset TCC permissions so VisionSight.app gets fresh camera/accessibility prompts
# (only needed if re-installing over a previous version)
tccutil reset Camera com.visionsight.app 2>/dev/null || true
tccutil reset Accessibility com.visionsight.app 2>/dev/null || true

echo "✅ Done! Open VisionSight from Applications."
echo "   → Camera permission will be requested on first launch."
echo "   → Grant Accessibility access in System Settings for auto-unlock."
INST_EOF
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