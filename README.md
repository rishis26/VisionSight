# VisionSight

> **Hands-free biometric auto-unlock for macOS.**  
> VisionSight watches your webcam in the background, recognizes your face the moment you wake your Mac, and types your password automatically — all entirely locally, with zero cloud, zero analytics, and zero tracking.

---

## Table of Contents

**Part I — Installation**
1. [Prerequisites](#1-prerequisites)
2. [Clone & Environment Setup](#2-clone--environment-setup)
3. [Install Dependencies](#3-install-dependencies)
4. [macOS Permissions](#4-macos-permissions)
5. [First-Time Setup (Keychain)](#5-first-time-setup-keychain)
6. [Register Your Face](#6-register-your-face)
7. [Install the Global CLI](#7-install-the-global-cli)
8. [Running VisionSight](#8-running-visionsight)

**Part II — Project Documentation**
9. [What is VisionSight?](#9-what-is-visionsight)
10. [How It Works](#10-how-it-works)
11. [Architecture](#11-architecture)
12. [File Structure](#12-file-structure)
13. [Features](#13-features)
14. [CLI Reference](#14-cli-reference)
15. [Configuration](#15-configuration)
16. [Security Model](#16-security-model)
17. [Tech Stack](#17-tech-stack)
18. [License](#18-license)

---

# Part I — Installation

## 1. Prerequisites

| Requirement | Details |
|---|---|
| **OS** | macOS 12 Monterey or later (Apple Silicon M1/M2/M3 or Intel) |
| **Python** | 3.10 or higher (`python3 --version`) |
| **Webcam** | Built-in FaceTime camera or any USB/external webcam |
| **Homebrew** | Required to install `cmake` and `dlib` dependencies |

Install Homebrew if you don't have it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install cmake (required for `dlib` which powers face recognition):
```bash
brew install cmake
```

---

## 2. Clone & Environment Setup

```bash
git clone https://github.com/rishis26/VisionSight.git
cd VisionSight
```

Create a virtual environment (keeps dependencies isolated):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **Note:** VisionSight always uses `.venv` inside the project directory. All CLI commands automatically re-execute inside this virtual environment — you don't need to manually activate it every time.

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Version | Purpose |
|---|---|---|
| `opencv-python` | 4.9.0.80 | Camera capture and frame processing |
| `face_recognition` | 1.3.0 | Face detection and identity encoding (powered by dlib) |
| `numpy` | 1.26.4 | Numerical operations for face encoding vectors |
| `python-dotenv` | 1.0.1 | Loading configuration from `.env` file |
| `PyQt6` | 6.10.2 | Native macOS GUI control panel |

PyObjC (required for macOS Cocoa integration) is bundled with the system Python on macOS. If missing:
```bash
pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz
```

---

## 4. macOS Permissions

VisionSight requires two macOS privacy permissions. These are prompted automatically on first launch, but you can grant them in advance:

### Camera Access
`System Settings → Privacy & Security → Camera → Terminal (or your IDE) → Enable`

### Accessibility Access
`System Settings → Privacy & Security → Accessibility → Terminal (or your IDE) → Enable`

> **Why Accessibility?** VisionSight uses the macOS Accessibility API to simulate keyboard input on the lock screen — typing your password character by character. Without this permission, unlocking will silently fail.

> **Important:** Permissions must be granted to **Terminal** (or **iTerm2**), not to Python itself, since VisionSight runs as a Python script launched from your terminal.

---

## 5. First-Time Setup (Keychain)

VisionSight needs to know your macOS login password so it can type it on the lock screen. It stores this **once**, encrypted in your macOS Hardware Keychain — it is never stored in plaintext on disk.

Run the setup wizard:
```bash
./visionsight setup
```

Or from the GUI: launch VisionSight and the **onboarding wizard** will walk you through it.

Your password is stored under the Keychain service name `VisionSightDaemon` and is retrieved securely at runtime using the macOS `security` command-line tool.

---

## 6. Register Your Face

VisionSight needs to learn what you look like before it can recognize you.

**Option A — via GUI (recommended):**
```bash
./visionsight gui
```
Navigate to the **Identities** tab → type your name → look at the camera → click **REGISTER ID**.

**Option B — via Terminal:**
```bash
./visionsight register <your-name>
```
Follow the prompt, press Enter when ready, and VisionSight captures and encodes your face in the background (no window or popup).

You can register **multiple identities** (e.g., family members) and all of them will be authorized to unlock.

---

## 7. Install the Global CLI

To use `visionsight` and the `vs` shorthand from any directory in your terminal:

```bash
./visionsight install
```

This does two things automatically:
1. **Creates a symlink** at `/usr/local/bin/visionsight` (you'll be prompted for your password via `sudo`)
2. **Adds `alias vs="visionsight"`** to your `~/.zshrc`

Then activate:
```bash
source ~/.zshrc
```

From now on, you can use `vs` or `visionsight` from anywhere:
```bash
vs start     # start protection in the system tray
vs gui       # open the dashboard
vs stop      # stop the daemon
```

---

## 8. Running VisionSight

### Start protection (background tray mode — recommended):
```bash
vs start
```
VisionSight runs silently in your macOS menu bar. It monitors screen lock events and automatically scans your face when you wake your Mac.

### Open the dashboard:
```bash
vs gui
```
If VisionSight is already running, this wakes and raises the existing window via macOS IPC — no duplicate processes.

### Stop protection:
```bash
vs stop
```

### Check if it's running:
```bash
vs status
```

---

# Part II — Project Documentation

## 9. What is VisionSight?

VisionSight is a **local-first, privacy-respecting facial recognition system** that replaces the manual step of typing your password every time you wake your Mac from sleep.

The moment your display wakes from sleep and your Mac's lock screen appears, VisionSight activates your webcam, runs face recognition in under a second, and if it sees your face — automatically types your password and unlocks the machine. The entire process takes less than 2 seconds from screen wake to unlocked desktop.

It is built entirely on open-source libraries, runs 100% on-device with no internet connection required, and stores your password only in your Mac's secure Hardware Keychain — the same place macOS stores Wi-Fi passwords and Apple ID credentials.

---

## 10. How It Works

### The Full Auto-Unlock Flow

```
Mac goes to sleep / screen locks
        ↓
macOS fires "screenIsLocked" notification
        ↓
VisionSight daemon thread receives it (Cocoa NSDistributedNotificationCenter)
        ↓
Display wakes → macOS fires "NSWorkspaceScreensDidWakeNotification"
        ↓
Daemon checks: is the system actually locked? (via CGSessionCopyCurrentDictionary)
        ↓
If yes → emits Qt signal to the main thread (thread-safe cross-thread signal)
        ↓
Main thread launches a DaemonScanThread (QThread — safe for cv2 on Apple Silicon)
        ↓
Camera opens (cv2.VideoCapture with CAP_AVFOUNDATION)
Camera warms up (auto-exposure adjustment, ~0.3s)
        ↓
Frames captured → downscaled to 280px width for speed
HOG face detector locates faces (~5ms per frame)
face_recognition encodes and matches against known identities
EAR (Eye Aspect Ratio) liveness check confirms eyes are open
        ↓
✅ Match found → SystemController.simulate_unlock()
   → Retrieves password from macOS Keychain
   → Wakes display (spacebar via CGEventPost)
   → Types password character by character (CGEventPost, 20ms intervals)
   → Sends Return key
        ↓
🔓 Mac unlocked
```

### Face Detection Pipeline

1. **Frame capture** — OpenCV reads frames at 30fps via `cv2.CAP_AVFOUNDATION` (Apple's native camera backend, 10x faster than the default backend on macOS)
2. **Downscaling** — Frames are scaled to 280px width before HOG detection, reducing computation by ~75% while maintaining accuracy
3. **Face location** — `face_recognition.face_locations()` with HOG model finds face bounding boxes (4–8ms per frame)
4. **Encoding** — `face_recognition.face_encodings()` computes a 128-dimensional face embedding vector
5. **Matching** — Euclidean distance between the live embedding and stored embeddings; threshold configurable (default: 0.55)
6. **Liveness check** — Eye Aspect Ratio (EAR) computed from 6 facial landmarks per eye; must exceed 0.25 to pass (prevents photo/sleeping spoofing)

---

## 11. Architecture

VisionSight is a **single-process, multi-threaded application** built on PyQt6 with a strict thread-safety model:

```
Process: gui/app.py (VisionSightGUI QMainWindow)
│
├── Main Thread — Qt event loop
│   ├── GUI rendering (PyQt6 widgets)
│   ├── Camera preview thread (CameraThread : QThread)
│   ├── Daemon scan thread (DaemonScanThread : QThread)
│   └── Signal/slot connections (all UI updates happen here)
│
└── Background Thread — Cocoa notification listener (DaemonCore)
    ├── NSDistributedNotificationCenter observer
    │   ├── com.apple.screenIsLocked → screenLocked_()
    │   ├── com.apple.screenIsUnlocked → screenUnlocked_()
    │   └── com.visionsight.show_gui → showGUI_() [IPC from CLI]
    └── NSWorkspace notification center observer
        ├── NSWorkspaceScreensDidSleepNotification → screenAsleep_()
        └── NSWorkspaceScreensDidWakeNotification → screenAwake_()
```

**Key design decisions:**
- `cv2.VideoCapture` is **only ever called from QThreads** — calling it from raw Python `threading.Thread` causes `EXC_BAD_INSTRUCTION` on Apple Silicon (macOS Sonoma)
- All cross-thread communication uses **Qt signals** (AutoConnection mode queues them onto the main event loop — fully thread-safe, no locks or polling needed)
- The Cocoa notification thread **never touches cv2 or face_recognition** — it only emits signals
- `CGEventPost(kCGHIDEventTap)` for keyboard injection **must be called from the main thread** — this is why unlocks are deferred via `scan_complete` signal

---

## 12. File Structure

```
VisionSight/
│
├── visionsight              # Universal CLI wrapper + entry point
│
├── main.py                  # Daemon core: Cocoa notification listener,
│                            # Qt signal bridge, DaemonBridge, DaemonCore
│
├── gui/
│   ├── app.py               # VisionSightGUI (QMainWindow) — main controller
│   │                        # Camera management, face registration, daemon wiring
│   ├── pages.py             # Modular page classes: Dashboard, Identities,
│   │                        # Settings, Security, Logs, Onboarding
│   ├── threads.py           # CameraThread (live preview), DaemonScanThread
│   └── widgets.py           # Reusable UI components: StyledButton, NavButton,
│                            # ToggleButton, SolidFrame, apply_shadow()
│
├── face_auth/
│   └── verify.py            # FaceVerifier — core recognition engine
│                            # (camera warmup, HOG detection, EAR liveness,
│                            #  encoding comparison, config hot-reload)
│
├── system/
│   ├── lock.py              # SystemController — lock state detection,
│   │                        # password retrieval from Keychain,
│   │                        # keyboard injection (CGEventPost)
│   ├── paths.py             # Centralized path management for all app data
│   │                        # (~/Library/Application Support/VisionSight/)
│   ├── unlock_helper        # Compiled C binary for privileged keyboard events
│   └── unlock_helper.c      # Source for the C unlock helper
│
├── assets/
│   └── icon.png             # Application icon (tray + dock + window)
│
├── setup.py                 # Standalone keychain password setup script
├── requirements.txt         # Python dependencies with pinned versions
└── .env                     # User configuration (auto-created, gitignored)
```

**App data** (stored outside the project, never in git):
```
~/Library/Application Support/VisionSight/
├── .env                     # Active configuration
├── logs/
│   └── daemon.log           # All runtime logs (append-only)
└── assets/
    └── known_faces/
        ├── encodings.pkl    # Face encoding vectors (encrypted pickle)
        └── <name>.jpg       # Captured registration photos
```

---

## 13. Features

### 🔓 Auto-Unlock
Detects the Mac lock screen using native Cocoa `NSDistributedNotificationCenter` events. Activates camera only when the screen wakes from lock — never runs continuously. Unlocks in under 2 seconds from display wake.

### 🪪 Multi-Identity Support
Register multiple people. All registered identities are authorized to unlock the machine. Manage them via the Identities tab or the CLI (`vs list`, `vs register`, `vs remove`).

### 👁 Liveness Detection (Anti-Spoofing)
Eye Aspect Ratio (EAR) computed from 6 facial landmarks per eye across a rolling 3-frame buffer. Eyes must be open above a threshold (EAR > 0.25) to pass — prevents unlock via a photograph, screenshot, or while asleep.

### 🔐 Hardware Keychain Storage
Your password is stored exactly once using macOS's `security` CLI tool into the Hardware Keychain under service name `VisionSightDaemon`. Retrieved at runtime via `security find-generic-password`. Never written to any file on disk.

### 🖥 Live Face Detection Badge
On the Identities page and Onboarding wizard, a real-time colored status badge below the camera preview shows:
- 🟢 **FACE DETECTED — READY** (green)
- 🔴 **NO FACE DETECTED** (red)
- 🟠 **MULTIPLE FACES** (orange)

Updated every ~300ms from a throttled background HOG scan on a half-resolution frame.

### 🖥 Neo-Brutalist Dashboard (GUI)
A bold, high-contrast PyQt6 control panel with 5 pages:
- **Overview** — daemon state, last auth event, live camera preview
- **Identities** — register/update/revoke face profiles with live preview
- **Config** — FPS, resolution, recognition tolerance, cooldown, auto-unlock toggle
- **System Sec** — change the stored keychain password
- **Log Files** — searchable, filterable audit log table

### 🧰 Full CLI Control
Every function exposed via the `visionsight` / `vs` CLI. No GUI required for headless/remote use. See [CLI Reference](#14-cli-reference).

### 📡 Process-to-Process IPC
If VisionSight is already running in the system tray, `vs gui` sends a `com.visionsight.show_gui` distributed notification via `NSDistributedNotificationCenter`. The running process receives it (registered with `NSNotificationSuspensionBehaviorDeliverImmediately`) and raises the dashboard window — no duplicate process launched.

### ⚡ Performance Optimized
- Camera opens in **~0.17 seconds** (vs ~2 seconds default) using `cv2.CAP_AVFOUNDATION`
- HOG face detection runs in **4–8ms** per frame (downscaled to 280px width)
- Camera preview runs at native **30 FPS** (5ms thread sleep vs 30ms default)
- Cocoa notification thread uses **0% CPU** at idle (CFRunLoopRunInMode with 100ms sleep, preventing busy-loop)

---

## 14. CLI Reference

```
COMMAND                              DESCRIPTION
─────────────────────────────────────────────────────────────────
vs                                   Launch the dashboard GUI
vs gui                               Launch / raise the dashboard GUI
vs start                             Start protection (minimized in system tray)
vs stop                              Stop the protection daemon
vs status                            Show whether daemon is running + PID
vs version                           Show version number

vs register <name>                   Register a new face identity (terminal mode)
vs remove <name>                     Remove a registered identity
vs list                              List all registered identities

vs config list                       Show all current configuration values
vs config set <key> <value>          Update a configuration value

vs logs                              Show last 20 lines of the daemon log
vs test                              Run a one-time face recognition test

vs setup                             Re-run the keychain password setup wizard
vs install                           Install globally (symlink + vs alias in ~/.zshrc)
```

---

## 15. Configuration

All configuration lives in `~/Library/Application Support/VisionSight/.env`. Edit via the GUI Config page or the CLI:

```bash
vs config list
vs config set VISIONSIGHT_TOLERANCE 0.5
```

| Key | Default | Description |
|---|---|---|
| `VISIONSIGHT_CAMERA` | `0` | Camera device index (0 = built-in, 1 = first external) |
| `VISIONSIGHT_TOLERANCE` | `0.55` | Face match threshold. Lower = stricter. Range: 0.4–0.7 |
| `VISIONSIGHT_AUTO_UNLOCK` | `true` | Whether to auto-type password after face match |
| `VISIONSIGHT_COOLDOWN` | `10` | Seconds to wait between scan attempts |
| `VISIONSIGHT_FPS` | `Medium` | Camera capture FPS hint (Low / Medium / High) |
| `VISIONSIGHT_RESOLUTION` | `640x480` | Camera capture resolution |

---

## 16. Security Model

| Aspect | Implementation |
|---|---|
| **Password storage** | macOS Hardware Keychain only — never on disk |
| **Face data** | 128-dim vectors stored locally in `encodings.pkl` — never uploaded |
| **Anti-spoofing** | EAR liveness check (eye openness) — rejects photos and sleeping users |
| **Network** | Zero network access — fully air-gapped operation |
| **Logs** | Append-only `daemon.log` in `~/Library/Application Support/VisionSight/logs/` |
| **Camera** | Only activated on screen wake events — never running in the background |
| **Permissions** | Camera + Accessibility granted to Terminal, not to a background daemon |

---

## 17. Tech Stack

| Layer | Technology |
|---|---|
| **GUI** | PyQt6 6.10 — native macOS Qt widgets |
| **Computer Vision** | OpenCV 4.9 with `cv2.CAP_AVFOUNDATION` (Apple native camera backend) |
| **Face Recognition** | `face_recognition` 1.3 (dlib HOG + ResNet face embeddings) |
| **macOS Integration** | PyObjC — `Foundation`, `AppKit`, `Quartz`, `CoreFoundation` |
| **IPC** | `NSDistributedNotificationCenter` (system-wide OS broadcast channel) |
| **Keychain** | macOS `security` CLI (`find-generic-password`, `add-generic-password`) |
| **Lock Detection** | `Quartz.CGSessionCopyCurrentDictionary()` — reads live session lock state |
| **Keyboard Injection** | `Quartz.CGEventPost(kCGHIDEventTap)` — injects key events at HID level |
| **Threading** | PyQt6 `QThread` for camera + scan workers, Python `threading.Thread` for Cocoa listener |
| **Config** | `python-dotenv` — `.env` file hot-reloaded before each scan |

---

## 18. License

MIT License — free to fork, modify, distribute, and use commercially.

Built by [Rishi Shah](https://github.com/rishis26).
