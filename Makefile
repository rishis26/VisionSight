PRODUCT      = VisionSight
BUILD_DIR    = .build/release
APP_BUNDLE   = $(PRODUCT).app
SWIFT_FLAGS  = --disable-sandbox -Xswiftc -Xfrontend -Xswiftc -disable-sandbox
ENV_FLAGS    = CLANG_MODULE_CACHE_PATH=/tmp/clang-cache

# ── Development ───────────────────────────────────────────────────────────────

.PHONY: build release run cli clean app install

build:
	$(ENV_FLAGS) swift build $(SWIFT_FLAGS)

release:
	$(ENV_FLAGS) swift build -c release $(SWIFT_FLAGS)

run:
	$(ENV_FLAGS) swift run $(SWIFT_FLAGS) VisionSightApp

cli:
	$(ENV_FLAGS) swift run $(SWIFT_FLAGS) vs $(ARGS)

clean:
	swift package clean
	rm -rf $(APP_BUNDLE)

# ── App Bundle (for distribution) ─────────────────────────────────────────────

.PHONY: app

app: release
	@echo "📦 Creating $(APP_BUNDLE)..."
	mkdir -p "$(APP_BUNDLE)/Contents/MacOS"
	mkdir -p "$(APP_BUNDLE)/Contents/Resources"
	cp "$(BUILD_DIR)/VisionSightApp" "$(APP_BUNDLE)/Contents/MacOS/$(PRODUCT)"
	cp Resources/Info.plist "$(APP_BUNDLE)/Contents/"
	@if [ -f assets/icon.icns ]; then \
		cp assets/icon.icns "$(APP_BUNDLE)/Contents/Resources/AppIcon.icns"; \
	fi
	codesign --force --sign - "$(APP_BUNDLE)"
	@echo "✅ $(APP_BUNDLE) created. Drag to /Applications or run directly."

# ── Install global CLI ────────────────────────────────────────────────────────

.PHONY: install

install: release
	@echo "Installing 'vs' CLI to /usr/local/bin..."
	sudo cp "$(BUILD_DIR)/vs" /usr/local/bin/vs
	@echo "✅ 'vs' command is now available globally."

