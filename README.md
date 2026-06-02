# VisionSight

> **Hands-free biometric auto-unlock for macOS.**  
> VisionSight watches your webcam in the background, recognizes your face the moment you wake your Mac, and types your password automatically.

> 🔒 **100% Offline. Nothing leaves your machine.** No cloud, no servers, no analytics, no accounts. Your face data and password never touch the internet — ever.

---

## Quick Setup

> Prerequisites: **macOS 12+**, **Python 3.10+**, **Homebrew**

```bash
# Install cmake (required for dlib / face recognition)
brew install cmake

# Clone and enter the project
git clone https://github.com/rishis26/VisionSight.git && cd VisionSight

# Create virtual environment and install dependencies
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Install the global CLI + vs shortcut
./visionsight install && source ~/.zshrc

# Run the app — onboarding will guide you through the rest
vs gui
```

That's it. The onboarding wizard handles permissions, keychain setup, and face registration.

---

## Detailed Setup

### What you need before starting

- **macOS 12 Monterey or later** — Apple Silicon (M1/M2/M3) or Intel
- **Python 3.10 or higher** — check with `python3 --version`
- **Homebrew** — macOS package manager. If you don't have it:
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
- **cmake** — required to compile `dlib`, the engine behind face recognition:
  ```bash
  brew install cmake
  ```

### Setting up the environment

Clone the repo and set up a Python virtual environment inside the project folder:

```bash
git clone https://github.com/rishis26/VisionSight.git
cd VisionSight
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The virtual environment is stored as `.venv/` inside the project. Once the global CLI is installed, every `vs` command automatically re-executes using `.venv/bin/python3` — so you never need to manually `source .venv/bin/activate` again.

### macOS Permissions

VisionSight needs two permissions — macOS will prompt for these on first launch. You can also grant them in advance:

**Camera Access** — to see your face  
`System Settings → Privacy & Security → Camera → Terminal → Enable`

**Accessibility Access** — to type your password on the lock screen  
`System Settings → Privacy & Security → Accessibility → Terminal → Enable`

> Permissions must be granted to **Terminal** (or iTerm2) — not to Python itself — because VisionSight runs as a script launched from your shell.

### Storing your password securely

VisionSight needs to know your macOS login password to unlock the screen. It asks for it **once**, then stores it encrypted in your **macOS Hardware Keychain** — the same vault macOS uses for Wi-Fi passwords and Apple ID credentials. It is never written to a file on disk.

Run the setup wizard:

```bash
vs setup
```

Or skip this — the onboarding screen inside the GUI will walk you through it automatically on first launch.

### Registering your face

VisionSight must learn what you look like before it can recognize you.

**Via the GUI (recommended for first time):**

```bash
vs gui
```

Go to the **Identities** tab → type your name → look at the camera → click **REGISTER ID**. A live badge below the camera shows whether your face is being detected in real time.

**Via terminal (no window needed):**

```bash
vs register YourName
```

Press Enter when prompted. VisionSight captures a frame in the background, detects your face, and saves the encoding — no GUI or popup required.

You can register **multiple people**. Everyone registered is authorized to unlock the machine.

### Installing the global CLI

To use `vs` or `visionsight` from any folder in your terminal:

```bash
./visionsight install
source ~/.zshrc
```

This does two things:

- Creates a symlink at `/usr/local/bin/visionsight` (you'll be prompted for your password once via `sudo`)
- Adds `alias vs="visionsight"` to your `~/.zshrc` — no hardcoded paths, works on any machine

### Running VisionSight

```bash
vs start      # Start protection silently in the system tray (recommended)
vs gui        # Open the control panel dashboard
vs stop       # Stop the daemon
vs status     # Check if it's running and show PID
```

Once `vs start` is running, VisionSight sits invisibly in the background. Every time your Mac wakes from sleep with the lock screen, it activates your camera, scans your face, and unlocks — automatically.

---

## About VisionSight

### What it is

VisionSight is a **local-first facial recognition auto-unlock system** for macOS. It replaces the repetitive step of typing your password every time your Mac wakes from sleep. The moment your display wakes, VisionSight sees your face and unlocks the machine — taking less than 2 seconds from screen wake to unlocked desktop.

Everything runs entirely on your computer. There is no server. No account. No subscription. No data collection. Your face encodings, password, logs, and configuration are all stored in `~/Library/Application Support/VisionSight/` on your local disk — and your password specifically lives only in the macOS Hardware Keychain, encrypted by the OS itself.

### How it works

When your Mac wakes from sleep, macOS fires a system notification. VisionSight's background thread catches it via Cocoa's `NSDistributedNotificationCenter`, checks whether the screen is actually locked via `Quartz.CGSessionCopyCurrentDictionary()`, and if so — opens the webcam and starts scanning.

Frames are downscaled to 280px width and run through a HOG face detector (4–8ms per frame). Detected faces are encoded into 128-dimensional vectors and compared against stored identity vectors using Euclidean distance. If the distance is below the configured tolerance threshold, the match passes.

A liveness check runs in parallel — computing Eye Aspect Ratio (EAR) from 6 facial landmarks per eye across a rolling frame buffer. Eyes must be open above a threshold to pass, which prevents unlocking via a photograph or while you're asleep.

On a successful match, VisionSight securely wakes the screen using the Shift key (preventing accidental password space injections), retrieves your password from the Keychain, and injects it as keyboard events via `Quartz.CGEventPost(kCGHIDEventTap)` — the same low-level HID event tap used by macOS accessibility tools.

### Architecture

VisionSight is a single-process, multi-threaded PyQt6 application with a strict thread-safety model:

```
Process: gui/app.py
│
├── Main Thread — Qt event loop
│   ├── All GUI rendering and widget updates
│   ├── CameraThread (QThread) — live camera preview at 30fps
│   └── DaemonScanThread (QThread) — face recognition on lock events
│
└── Background Thread — Cocoa notification listener
    ├── com.apple.screenIsLocked / screenIsUnlocked
    ├── NSWorkspaceScreensDidSleep / DidWake
    └── com.visionsight.show_gui  ← IPC from CLI
```

`cv2.VideoCapture` is only ever called from QThreads — raw Python threads cause crashes on Apple Silicon. All cross-thread communication happens via Qt signals (queued onto the main event loop, fully thread-safe, no mutexes needed).

When `vs gui` is run while the app is already in the tray, it posts a `com.visionsight.show_gui` distributed notification. The running process receives it instantly (registered with `NSNotificationSuspensionBehaviorDeliverImmediately`) and raises the existing window — no duplicate process.

### File structure

```
VisionSight/
├── visionsight          ← CLI entry point (auto re-executes in .venv)
├── main.py              ← Daemon core: Cocoa listeners + Qt signal bridge
├── gui/
│   ├── app.py           ← Main controller (VisionSightGUI QMainWindow)
│   ├── pages.py         ← Dashboard, Identities, Settings, Security, Logs, Onboarding
│   ├── threads.py       ← CameraThread, DaemonScanThread
│   └── widgets.py       ← Reusable UI components
├── face_auth/
│   └── verify.py        ← FaceVerifier (HOG detection, EAR liveness, encoding match)
├── system/
│   ├── lock.py          ← SystemController (lock detection, keychain, keyboard inject)
│   ├── paths.py         ← Centralized app data paths
│   └── unlock_helper    ← Compiled C binary for privileged key events
├── assets/icon.png
├── setup.py             ← Standalone keychain password wizard
└── requirements.txt
```

App data (outside the project, never committed):

```
~/Library/Application Support/VisionSight/
├── .env                 ← Active configuration
├── logs/daemon.log      ← Append-only runtime log
└── assets/known_faces/
    ├── encodings.pkl    ← Face embedding vectors
    └── <name>.jpg       ← Registration photos
```

### Features

**Auto-Unlock** — Activates only on lock screen wake events, never runs the camera in the background continuously. Unlocks in under 2 seconds.

**Multi-Identity** — Register multiple people. All are authorized to unlock. Manage via GUI or CLI.

**Liveness Detection** — Eye Aspect Ratio check prevents unlocking from a photo or while asleep.

**Live Face Badge** — On the Identities page, a real-time colored pill shows whether your face is being detected (green), not detected (red), or multiple faces are visible (orange) — updated every ~300ms.

**Hardware Keychain** — Password stored once in macOS Keychain, retrieved securely at runtime. Never written to a file.

**IPC Window Activation** — `vs gui` raises the existing tray window instantly via macOS distributed notifications — no duplicate process.

**Full CLI** — Every function accessible from the terminal. No GUI required.

**Clean Dark Mode Dashboard** — Sleek Apple-native PyQt6 control panel with Overview, Identities, Config, Security, and Logs pages.

### CLI Reference

| Command                     | Description                                            |
| --------------------------- | ------------------------------------------------------ |
| `vs` / `vs gui`             | Open the dashboard (raises existing window if running) |
| `vs start`                  | Start protection in the system tray                    |
| `vs stop`                   | Stop the daemon                                        |
| `vs status`                 | Show running state and PID                             |
| `vs register <name>`        | Register a face (terminal mode, no GUI)                |
| `vs remove <name>`          | Remove a registered identity                           |
| `vs list`                   | List all registered identities                         |
| `vs config list`            | Show all config values                                 |
| `vs config set <key> <val>` | Update a config value                                  |
| `vs logs`                   | Show last 20 lines of daemon log                       |
| `vs test`                   | One-time face recognition test                         |
| `vs setup`                  | Re-run the keychain password wizard                    |
| `vs install`                | Install globally + add `vs` alias to `~/.zshrc`        |

### Configuration

Stored in `~/Library/Application Support/VisionSight/.env`. Edit via GUI Config page or `vs config set`.

| Key                       | Default   | Description                                          |
| ------------------------- | --------- | ---------------------------------------------------- |
| `VISIONSIGHT_CAMERA`      | `0`       | Camera index (0 = built-in, 1 = first external)      |
| `VISIONSIGHT_TOLERANCE`   | `0.55`    | Match threshold — lower is stricter (range: 0.4–0.7) |
| `VISIONSIGHT_AUTO_UNLOCK` | `true`    | Auto-type password after a face match                |
| `VISIONSIGHT_COOLDOWN`    | `10`      | Seconds between scan attempts                        |
| `VISIONSIGHT_FPS`         | `Medium`  | Camera FPS hint (Low / Medium / High)                |
| `VISIONSIGHT_RESOLUTION`  | `640x480` | Capture resolution                                   |

### Tech Stack

|                    | Technology                                            |
| ------------------ | ----------------------------------------------------- |
| GUI                | PyQt6 6.10                                            |
| Camera             | OpenCV 4.9 with `cv2.CAP_AVFOUNDATION`                |
| Face Recognition   | `face_recognition` 1.3 (dlib HOG + ResNet embeddings) |
| macOS APIs         | PyObjC — Foundation, AppKit, Quartz, CoreFoundation   |
| IPC                | `NSDistributedNotificationCenter`                     |
| Lock Detection     | `Quartz.CGSessionCopyCurrentDictionary()`             |
| Keyboard Injection | `Quartz.CGEventPost(kCGHIDEventTap)`                  |
| Password Storage   | macOS `security` CLI + Hardware Keychain              |

---

MIT License. Built by [Rishi Shah](https://github.com/rishis26).
