# VisionSight

VisionSight is an open-source, background facial recognition system that automatically unlocks your macOS lock screen when it sees you. 
It uses OpenCV, `face_recognition`, and macOS native Cocoa APIs to monitor the screen lock state and securely type your password for you when a recognized face is in front of the camera.

## Features
- **Auto-Unlock**: Detects when the Mac is locked, wakes up the screen, checks the webcam, and enters your password automatically.
- **Biometric Liveness Check**: Validates Eye Aspect Ratio (EAR) to ensure eyes are open (prevents unlocking while asleep/preventing photo spoofing).
- **Secure Keychain Storage**: The application asks for your password once during setup and encrypts it safely into the macOS Hardware Keychain.
- **Neo-Brutalist Dashboard**: A modern PyQt6 control panel to configure identities, tweak confidence thresholds, and view logs.
- **Fully Open Source**: No cloud, no analytics, no remote servers. Everything runs entirely locally on your machine.

## Prerequisites
- macOS (Apple Silicon / M-series or Intel)
- Python 3.10 or higher
- A built-in or external webcam

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/rishis26/VisionSight.git
   cd VisionSight
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Usage

### 1. Initial Setup
Run the setup script to securely store your macOS login password in your keychain. This is required so VisionSight can unlock your screen automatically:
```bash
python setup.py
```

### 2. Start the Application
Run the main script to launch the VisionSight Daemon and Control Panel:
```bash
python main.py
```
*(On first run, navigate to the Dashboard/Onboarding screen to register your face).*

## macOS Permissions
When you run the application for the first time, macOS will ask for:
- **Camera Access**: To scan your face.
- **Accessibility Access**: To inject keyboard events (typing your password) on the lock screen.

If auto-unlock fails, ensure Python/Terminal has Accessibility permissions under `System Settings -> Privacy & Security -> Accessibility`.

## License
MIT License. Feel free to fork, modify, and improve.
