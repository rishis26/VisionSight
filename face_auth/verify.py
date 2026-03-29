import cv2
import face_recognition
import pickle
import os
import math
import numpy as np
import time
import threading
import sys
import sys
from collections import deque

from dotenv import load_dotenv

load_dotenv()

class FaceVerifier:
    def __init__(self, encodings_path="assets/known_faces/encodings.pkl", video_source=0, on_lock=None, on_unlock=None, headless=True):
        print("Initializing Advanced Identity Verification Engine...")
        
        # Load configurable options from .env
        self.video_source = int(os.getenv("VISIONSIGHT_CAMERA", video_source))
        self.TOLERANCE = float(os.getenv("VISIONSIGHT_TOLERANCE", 0.45))

        self.headless = headless
        self.on_lock = on_lock
        self.on_unlock = on_unlock
        
        self.encodings_path = encodings_path
        self.known_names = []
        self.known_encodings = []
        self.load_known_faces()
        self.EYE_AR_THRESH = 0.25
        self.EAR_BUFFER_SIZE = 3
        self.ear_history = deque(maxlen=self.EAR_BUFFER_SIZE)
        
        self.blink_count = 0
        self.eye_closed_last_frame = False
        
        self.is_authenticated = False
        self.blink_at_verify = 0
        self.auth_name = None
        self.last_blink_time = 0
        
        self.frames_absent = 0
        self.frames_unauthorized = 0
        
        self._stop_requested = False

        print(f"System Ready. Recognition Tolerance: {self.TOLERANCE}")
        self.cap = None

    def load_known_faces(self):
        if not os.path.exists(self.encodings_path):
            print(f"ERROR: Encodings file not found at {self.encodings_path}")
            return
        with open(self.encodings_path, "rb") as f:
            data = pickle.load(f)
            self.known_names = list(data.keys())
            self.known_encodings = list(data.values())
            print(f"Loaded {len(self.known_names)} authorized identity: {self.known_names}")

    def calculate_ear(self, eye):
        A = math.dist(eye[1], eye[5])
        B = math.dist(eye[2], eye[4])
        C = math.dist(eye[0], eye[3])
        return (A + B) / (2.0 * C)

    def _release_camera(self):
        """Safely release camera and destroy any windows."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
        print("📷 Camera released.")



    def authenticate_once(self, system_controller):
        """
        Returns one of four states:
        - 'success'  : face matched and unlock triggered
        - 'rejected' : user pressed Esc — they want to type password manually
        - 'aborted'  : screen unlocked by other means mid-scan
        - 'failed'   : webcam error
        """
        print("🟢 CAMERA WARMUP: Booting webcam session...")
        self.cap = cv2.VideoCapture(self.video_source)
        
        if not self.cap.isOpened():
            print("⚠️ Error: Could not open webcam.")
            return "failed"

        print("👁️‍🗨️ SCANNING: Waiting for authorized face... (Press Esc to stop)")

        self.is_authenticated = False
        self.auth_name = None
        self.frames_absent = 0
        self.frames_unauthorized = 0
        self._stop_requested = False

        # Admin-Level Hook: Catch Esc key securely across the entire OS (bypassing Lock Screen event swallowing)
        def on_press(key):
            try:
                from pynput import keyboard
                if key == keyboard.Key.esc:
                    print("\n🛑 Admin Hardware Hook: Esc key intercepted globally!")
                    self._stop_requested = True
                    return False  # Kill the keyboard listener
            except Exception:
                pass

        try:
            from pynput import keyboard
            esc_listener = keyboard.Listener(on_press=on_press)
            esc_listener.start()
        except Exception as e:
            print(f"⚠️ Could not start pynput listener: {e}")
            esc_listener = None

        last_display_check = time.time()

        while True:
            # Check physical hardware display state strictly every 1.0s to catch idle sleep
            current_time = time.time()
            if current_time - last_display_check >= 1.0:
                if not system_controller._is_display_on():
                    self._stop_requested = True
                last_display_check = current_time

            if self._stop_requested:
                print("🛑 Scan aborted by OS/User event (Esc/Sleep).")
                self._release_camera()
                if esc_listener:
                    esc_listener.stop()
                return "rejected"

            # ── ABORT: screen no longer locked ──────────────────────────────
            if not system_controller._is_macos_locked():
                print("🛑 ABORT: Screen unlocked externally.")
                self._release_camera()
                if esc_listener:
                    esc_listener.stop()
                return "aborted"

            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ Webcam read failed.")
                self._release_camera()
                if esc_listener:
                    esc_listener.stop()
                return "failed"

            # Non-headless Esc via cv2 window
            if not self.headless:
                key_cv = cv2.waitKey(1) & 0xFF
                if key_cv == 27:
                    print("🛑 Esc pressed.")
                    self._release_camera()
                    if esc_listener:
                        esc_listener.stop()
                    return "rejected"

            # --- Preprocessing ---
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            small_face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")

            if not small_face_locations:
                if not self.headless:
                    cv2.imshow('VisionSight - Secure Biometric Session', frame)
                else:
                    time.sleep(0.01)
                continue

            face_locations = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in small_face_locations]
            face_landmarks_list = face_recognition.face_landmarks(rgb_frame, face_locations)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            auth_user_present = False
            unauthorized_user_present = False

            for (top, right, bottom, left), landmarks, encoding in zip(face_locations, face_landmarks_list, face_encodings):

                # -----------------------------------------------------
                # LIVENESS CHECK: Are the eyes open?
                # -----------------------------------------------------
                if 'left_eye' in landmarks and 'right_eye' in landmarks:
                    left_ear = self.calculate_ear(landmarks['left_eye'])
                    right_ear = self.calculate_ear(landmarks['right_eye'])
                    ear = (left_ear + right_ear) / 2.0
                    
                    # If EAR is too low, the eyes are closed. Reject unlock.
                    if ear < self.EYE_AR_THRESH:
                        print(f"⚠️ Liveness Failed: Eyes are closed (EAR: {ear:.2f}). Denying unlock access.")
                        continue
                # -----------------------------------------------------

                name = "Unknown"
                color = (0, 0, 255)
                match_distance = 1.0

                if self.known_encodings:
                    face_distances = face_recognition.face_distance(self.known_encodings, encoding)
                    best_match_index = np.argmin(face_distances)
                    match_distance = face_distances[best_match_index]

                    if match_distance < self.TOLERANCE:
                        name = self.known_names[best_match_index]
                        auth_user_present = True

                        if not self.is_authenticated:
                            print(f"✅ Identity Verified! Authenticated as {name}.")
                            self.is_authenticated = True
                            self.auth_name = name

                            # Release camera FIRST — light off before screen wakes
                            self._release_camera()
                            if esc_listener:
                                esc_listener.stop()

                            # Then unlock
                            system_controller.simulate_unlock(name)
                            return "success"
                    else:
                        unauthorized_user_present = True
                else:
                    unauthorized_user_present = True

                if not self.headless:
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    confidence_score = 1.0 - (match_distance / 2.0)
                    cv2.putText(frame, f"{name.title()} ({confidence_score:.1%})", (left + 6, bottom - 6),
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
                    for p in landmarks['left_eye'] + landmarks['right_eye']:
                        cv2.circle(frame, (p[0], p[1]), 2, (255, 255, 0), -1)

            if unauthorized_user_present and not auth_user_present:
                self.frames_unauthorized += 1
                if self.frames_unauthorized > 5:
                    self.frames_unauthorized = 0
                    if self.on_lock:
                        self.on_lock(reason="Unauthorized entity detected")
            else:
                self.frames_unauthorized = 0

            if not self.headless:
                cv2.imshow('VisionSight - Secure Biometric Session', frame)

        self._release_camera()
        if esc_listener:
            esc_listener.stop()
        return "aborted"

if __name__ == "__main__":
    from system.lock import SystemController
    verifier = FaceVerifier()
    verifier.authenticate_once(SystemController())