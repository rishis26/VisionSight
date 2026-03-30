# VisionSight Distribution Guide

## Pre-Distribution Checklist

### Code Quality
- [ ] All tests passing
- [ ] No debug print statements
- [ ] Error handling in place
- [ ] Logging configured properly
- [ ] Code reviewed and approved

### Security
- [ ] No hardcoded credentials
- [ ] Keychain integration tested
- [ ] Permissions properly requested
- [ ] Face data encrypted at rest
- [ ] No telemetry without consent

### Testing
- [ ] Tested on Apple Silicon Mac
- [ ] Tested on Intel Mac
- [ ] Tested on macOS 11, 12, 13, 14
- [ ] Camera permissions work
- [ ] Accessibility permissions work
- [ ] Auto-unlock works reliably
- [ ] Daemon starts/stops correctly
- [ ] Uninstaller works completely

### Documentation
- [ ] README.md updated
- [ ] INSTALL.md complete
- [ ] BUILD.md accurate
- [ ] Changelog updated
- [ ] License file included

## Build for Distribution

### 1. Clean Build
```bash
# Remove all previous builds
rm -rf build dist venv __pycache__
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# Fresh virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller dmgbuild

# Build
./build_mac_app.sh
```

### 2. Code Signing (Required for Distribution)

#### Get Developer ID Certificate
1. Enroll in Apple Developer Program ($99/year)
2. Create Developer ID Application certificate
3. Download and install in Keychain

#### Sign the App
```bash
# Find your certificate
security find-identity -v -p codesigning

# Sign with Developer ID
codesign --force --deep \
    --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --options runtime \
    --entitlements entitlements.plist \
    dist/VisionSight.app

# Verify signature
codesign -vvv --deep --strict dist/VisionSight.app
spctl -a -vvv -t install dist/VisionSight.app
```

#### Create Entitlements File
```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
```

### 3. Notarization (Required for macOS 10.15+)

#### Setup
```bash
# Store credentials in keychain
xcrun notarytool store-credentials "AC_PASSWORD" \
    --apple-id "your@email.com" \
    --team-id "TEAM_ID" \
    --password "app-specific-password"
```

#### Create Signed DMG
```bash
# Create DMG
hdiutil create -volname "VisionSight" \
    -srcfolder dist/VisionSight.app \
    -ov -format UDZO \
    dist/VisionSight.dmg

# Sign DMG
codesign --force --sign "Developer ID Application: Your Name (TEAM_ID)" \
    dist/VisionSight.dmg
```

#### Submit for Notarization
```bash
# Submit
xcrun notarytool submit dist/VisionSight.dmg \
    --keychain-profile "AC_PASSWORD" \
    --wait

# Check status
xcrun notarytool info SUBMISSION_ID \
    --keychain-profile "AC_PASSWORD"

# Staple ticket to DMG
xcrun stapler staple dist/VisionSight.dmg

# Verify
xcrun stapler validate dist/VisionSight.dmg
spctl -a -vvv -t install dist/VisionSight.dmg
```

## Distribution Channels

### 1. GitHub Releases
```bash
# Create release
gh release create v1.0.0 \
    dist/VisionSight.dmg \
    --title "VisionSight v1.0.0" \
    --notes "Release notes here"
```

### 2. Direct Download
- Host DMG on your website
- Provide SHA256 checksum
- Include installation instructions

```bash
# Generate checksum
shasum -a 256 dist/VisionSight.dmg > dist/VisionSight.dmg.sha256
```

### 3. Homebrew Cask (Optional)
```ruby
# visionsight.rb
cask "visionsight" do
  version "1.0.0"
  sha256 "checksum_here"

  url "https://github.com/user/visionsight/releases/download/v#{version}/VisionSight.dmg"
  name "VisionSight"
  desc "Face recognition auto-unlock for macOS"
  homepage "https://github.com/user/visionsight"

  app "VisionSight.app"

  zap trash: [
    "~/Library/Application Support/VisionSight",
    "~/Library/LaunchAgents/com.visionsight.daemon.plist",
  ]
end
```

## Release Process

### 1. Version Bump
```bash
# Update version in code
VERSION="1.0.0"

# Tag release
git tag -a v$VERSION -m "Release v$VERSION"
git push origin v$VERSION
```

### 2. Build Release
```bash
./build_mac_app.sh
```

### 3. Test Release Build
```bash
# Test on clean system
# - Fresh macOS install or VM
# - No development tools installed
# - Test complete user flow
```

### 4. Sign and Notarize
```bash
# Sign
codesign --force --deep --sign "Developer ID" dist/VisionSight.app

# Create DMG
hdiutil create -volname "VisionSight" -srcfolder dist/VisionSight.app -ov -format UDZO dist/VisionSight.dmg

# Sign DMG
codesign --force --sign "Developer ID" dist/VisionSight.dmg

# Notarize
xcrun notarytool submit dist/VisionSight.dmg --keychain-profile "AC_PASSWORD" --wait

# Staple
xcrun stapler staple dist/VisionSight.dmg
```

### 5. Upload Release
```bash
# GitHub
gh release create v$VERSION dist/VisionSight.dmg

# Or manually upload to hosting
```

### 6. Announce Release
- Update website
- Post on social media
- Email newsletter
- Update documentation

## Analytics (Optional)

### Privacy-Respecting Analytics
```python
# Only collect:
# - App version
# - macOS version
# - Install/uninstall events
# - Crash reports (with user consent)

# Never collect:
# - Face data
# - Passwords
# - Personal information
# - Usage patterns
```

## Support Plan

### Documentation
- Comprehensive README
- Video tutorials
- FAQ section
- Troubleshooting guide

### Issue Tracking
- GitHub Issues for bug reports
- Feature request template
- Bug report template

### Community
- Discord/Slack channel
- Email support
- Response time SLA

## Legal Considerations

### License
- Choose appropriate license (MIT, GPL, etc.)
- Include LICENSE file
- Add copyright notices

### Privacy Policy
- Explain data collection (none for VisionSight)
- Explain local storage
- Explain permissions needed

### Terms of Service
- Liability disclaimer
- Warranty disclaimer
- Usage restrictions

## Marketing Materials

### Screenshots
- App interface
- Setup wizard
- Settings panel
- Face registration

### Demo Video
- Installation process
- First-time setup
- Auto-unlock demo
- Configuration options

### Website
- Landing page
- Download button
- Documentation
- Support contact

## Post-Release

### Monitor
- Download statistics
- Issue reports
- User feedback
- Crash reports

### Update Cycle
- Bug fixes: As needed
- Minor updates: Monthly
- Major updates: Quarterly

### Deprecation Policy
- Support last 3 macOS versions
- 6-month notice for breaking changes
- Migration guides for major updates
