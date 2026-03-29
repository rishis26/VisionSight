#!/bin/bash
set -e

echo "===================================="
echo "🍏 VISIONSIGHT DMG BUILDER 🍏"
echo "===================================="

# Clean up previous builds
rm -rf build dist
mkdir -p build/assets

echo "[1/4] Building Background Daemon (VisionSightDaemon)..."
pyinstaller --noconfirm --onedir -n VisionSightDaemon main.py

echo "[2/4] Building Native App UI (VisionSight.app)..."
# We include known_faces dummy and the icon
pyinstaller --noconfirm --windowed --icon=assets/icon.png --add-data "assets:assets" -n VisionSight gui/app.py

echo "[3/4] Integrating Architecture into App Bundle..."
# Move the compiled daemon into the MacOS bundle folder of the main app
cp -R dist/VisionSightDaemon/* dist/VisionSight.app/Contents/MacOS/
chmod +x dist/VisionSight.app/Contents/MacOS/VisionSightDaemon

echo "[4/4] Creating DMG Installer..."
# Wrap the VisionSight.app into a deployable DMG package
cd dist
dmgbuild -s ../dmg_settings.py "VisionSight" VisionSight.dmg || echo "dmgbuild failed, but VisionSight.app is ready in dist/"

echo "===================================="
echo "✅ BUILD COMPLETE!"
echo "Your app is ready at: dist/VisionSight.app"
echo "DMG Installer (if successful) is at: dist/VisionSight.dmg"
echo "===================================="
