import cv2
import face_recognition
import pickle
import os
import math
import numpy as np
import time
from collections import deque

class FaceVerifier:
    def __init__(self, encodings_path="assets/known_faces/encodings.pkl", video_source=0, on_lock=None, on_unlock=None):
        print("Initializing Advanced Identity Verification Engine...")
        
        # Architecture Callbacks
        self.on_lock = on_lock
        self.on_unlock = on_unlock
        
        # 1. Load Known Encodings
        self.encodings_path = encodings_path
        self.known_names = []
        self.known_encodings = []
        self.load_known_faces()

        # 2. Setup Webcam
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            raise Exception("Error: Could not open video source.")

        # 3. Sensitivity & State Settings (High Accuracy Mode)
        self.TOLERANCE = 0.42        # Strict tolerance (Default was 0.6, 0.42 is highly secure)
        self.EYE_AR_THRESH = 0.25    # EAR threshold for blinks (increased for fast blinks)
        self.EAR_BUFFER_SIZE = 3     # Reduced for faster reactivity
        self.ear_history = deque(maxlen=self.EAR_BUFFER_SIZE)
        
        # Biometric State
        self.blink_count = 0
        self.eye_closed_last_frame = False
        
        # Authentication State
        self.is_authenticated = False
        self.blink_at_verify = 0
        self.auth_name = None
        self.last_blink_time = 0

        print(f"System Ready. Recognition Tolerance: {self.TOLERANCE}")

    def load_known_faces(self):
        """Loads the biometric signatures from the serialized pickle file."""
        if not os.path.exists(self.encodings_path):
            print(f"ERROR: Encodings file not found at {self.encodings_path}")
            return

        with open(self.encodings_path, "rb") as f:
            data = pickle.load(f)
            self.known_names = list(data.keys())
            self.known_encodings = list(data.values())
            print(f"Loaded {len(self.known_names)} authorized identity: {self.known_names}")

    def calculate_ear(self, eye):
        """Calculates Eye Aspect Ratio (EAR)."""
        A = math.dist(eye[1], eye[5])
        B = math.dist(eye[2], eye[4])
        C = math.dist(eye[0], eye[3])
        return (A + B) / (2.0 * C)

    def run(self):
        """Main recognition loop with Liveness Challenge."""
        print("Starting Secure Biometric Session... Press 'q' to logout.")

        while True:
            ret, frame = self.cap.read()
            if not ret: break

            # --- Mirror & Preprocessing ---
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Create a 0.5x frame solely for rapid Face Detection (fixes the FPS issue)
            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # 1. Find Face Bounding Boxes on the SMALL frame (Lighting fast)
            small_face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            
            # Pre-scale coordinate locations back to 1.0x size
            face_locations = []
            for (top, right, bottom, left) in small_face_locations:
                face_locations.append((top * 2, right * 2, bottom * 2, left * 2))

            # 2. Extract Landmarks & Encodings from the FULL frame using the coordinates (High Accuracy)
            face_landmarks_list = face_recognition.face_landmarks(rgb_frame, face_locations)
            
            # Removed num_jitters=2 to save FPS. (The 100-jitter base encoding is accurate enough).
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            # Tracking if users are present
            auth_user_present = False
            unauthorized_user_present = False

            # 2. Process each face found
            for (top, right, bottom, left), landmarks, encoding in zip(face_locations, face_landmarks_list, face_encodings):
                # We are using the full frame now, so no need to scale coordinates up
                # top *= 2; right *= 2; bottom *= 2; left *= 2

                # --- 2a. Identity Matching ---
                name = "Unknown"
                color = (0, 0, 255) # Red for Unknown
                match_distance = 1.0

                if self.known_encodings:
                    face_distances = face_recognition.face_distance(self.known_encodings, encoding)
                    best_match_index = np.argmin(face_distances)
                    match_distance = face_distances[best_match_index]

                    if match_distance < self.TOLERANCE:
                        name = self.known_names[best_match_index]
                        auth_user_present = True
                        
                        # --- Liveness Challenge Stage Logic ---
                        if not self.is_authenticated:
                            # Stage 1: Identity Verified, Waiting for Blink
                            if self.auth_name != name:
                                self.auth_name = name
                                self.blink_at_verify = self.blink_count
                            
                            color = (255, 100, 0) # Blue-ish for "Challenge Mode"
                            status_text = "VERIFIED | BLINK TO UNLOCK"
                        else:
                            # Stage 2: Fully Authenticated
                            color = (0, 255, 0) # Green for Access Granted
                            status_text = "ACCESS GRANTED"
                    else:
                        # Distance > Tolerance = Unknown user
                        unauthorized_user_present = True
                else:
                    unauthorized_user_present = True
                
                # --- 2b. Eye Tracking (EAR) ---
                left_ear = self.calculate_ear(landmarks['left_eye'])
                right_ear = self.calculate_ear(landmarks['right_eye'])
                avg_ear = (left_ear + right_ear) / 2.0
                
                self.ear_history.append(avg_ear)
                smoothed_ear = np.mean(self.ear_history)
                eye_closed = smoothed_ear < self.EYE_AR_THRESH

                # Blink Logic
                if not eye_closed and self.eye_closed_last_frame:
                    self.blink_count += 1
                    current_time = time.time()
                    time_since_last_blink = current_time - self.last_blink_time
                    self.last_blink_time = current_time

                    # 1. Check for Double-Blink (Lock Gesture)
                    if self.is_authenticated and time_since_last_blink < 0.8:
                        print("Double-Blink Gesture Detected! Re-locking session...")
                        self.is_authenticated = False
                        self.auth_name = None
                        if self.on_lock: self.on_lock(reason="Double-Blink Gesture")

                    # 2. Check if this blink completes the challenge
                    elif auth_user_present and not self.is_authenticated:
                        if self.blink_count > self.blink_at_verify:
                            print(f"Liveness Challenge Passed! Authenticated as {name}.")
                            self.is_authenticated = True
                            if self.on_unlock: self.on_unlock(user_name=name)
                
                self.eye_closed_last_frame = eye_closed

                # --- 2c. Drawing & HUD ---
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # Top Status (Action Required)
                cv2.putText(frame, status_text if name != "Unknown" else "UNKNOWN", 
                            (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Bottom Identity Label & Confidence Score
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                
                # Convert raw math L1/L2 distance to a "Confidence Score"
                # A distance of 0.4 is incredibly accurate in AI, so we map it to ~80%
                confidence_score = 1.0 - (match_distance / 2.0)  
                
                cv2.putText(frame, f"{name.title()} ({confidence_score:.1%})", (left + 6, bottom - 6), 
                            cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)

                # Eye Markers (Visual feedback)
                for p in landmarks['left_eye'] + landmarks['right_eye']:
                    cv2.circle(frame, (p[0], p[1]), 2, (255, 255, 0), -1)

            # 3. Security Triggers for Lock Controller
            # Rule A: Authorized user stepped away
            if not auth_user_present and self.is_authenticated:
                print("Authorized user left. Resetting authentication...")
                self.is_authenticated = False
                self.auth_name = None
                if self.on_lock: self.on_lock(reason="Authorized user stepped away")

            # Rule B: Unauthorized face detected while not authenticated
            if unauthorized_user_present and not auth_user_present:
               # Trigger lockdown if an unknown face is on camera
               if self.on_lock: self.on_lock(reason="Unauthorized entity detected")

            # 4. Render Session
            cv2.imshow('VisionSight - Secure Biometric Session', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        print(f"Session Terminated. Final Blink Count: {self.blink_count}")

if __name__ == "__main__":
    verifier = FaceVerifier()
    verifier.run()
