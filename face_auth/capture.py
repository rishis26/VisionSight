import cv2
import face_recognition
import numpy as np
import math
from collections import deque

class FaceDetector:
    def __init__(self, video_source=0):
        print("Initializing Advanced VisionSight Capture System (V2)...")
        self.cap = cv2.VideoCapture(video_source)
        
        if not self.cap.isOpened():
            raise Exception("Error: Could not open video source.")

        # EAR Thresholds (Sensitivity Settings)
        self.EYE_AR_THRESH = 0.22  # Slightly increased for higher resolution
        self.EAR_BUFFER_SIZE = 5   # Number of frames to average
        self.ear_history = deque(maxlen=self.EAR_BUFFER_SIZE)
        
        # Blink Counter Stat
        self.blink_count = 0
        self.eye_closed_last_frame = False

        print(f"Webcam successfully initialized.")
        print(f"Accuracy Settings: Resolution x0.5, Temporal Smoothing {self.EAR_BUFFER_SIZE} frames.")

    def calculate_ear(self, eye):
        """
        Calculate Eye Aspect Ratio (EAR) for a single eye.
        Formula: (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        A = math.dist(eye[1], eye[5])
        B = math.dist(eye[2], eye[4])
        C = math.dist(eye[0], eye[3])
        
        ear = (A + B) / (2.0 * C)
        return ear

    def run(self):
        """
        Main loop to capture frames, detect faces, landmarks, and eye state with temporal smoothing.
        """
        print("Starting precision biometric scanning... Press 'q' to quit.")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Could not read frame.")
                break

            # --- Mirror the frame for a more natural preview ---
            frame = cv2.flip(frame, 1)

            # 1. Resize to 0.5 (Higher detail for accuracy)
            small_frame = cv2.resize(frame, (0, 0), fx=0.50, fy=0.50)
            # 2. BGR to RGB
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # 3. Get Face Locations & Landmarks (using 0.5 scaled image)
            face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)

            # 4. Process each face detected
            for (top, right, bottom, left), face_landmarks in zip(face_locations, face_landmarks_list):
                # Scale coordinates back up (factor of 2 now instead of 4)
                top *= 2; right *= 2; bottom *= 2; left *= 2

                # --- 4a. Face Bounding Box ---
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                # --- 4b. Eye Detection Logic ---
                left_eye = face_landmarks['left_eye']
                right_eye = face_landmarks['right_eye']

                # Calculate EAR for both eyes
                left_ear = self.calculate_ear(left_eye)
                right_ear = self.calculate_ear(right_eye)
                avg_ear = (left_ear + right_ear) / 2.0

                # --- 4c. Temporal Smoothing (Debounce Logic) ---
                self.ear_history.append(avg_ear)
                smoothed_ear = np.mean(self.ear_history)

                # --- 4d. Draw Landmarks (Dots on Eyes) ---
                for point in left_eye + right_eye:
                    px, py = point[0] * 2, point[1] * 2
                    cv2.circle(frame, (px, py), 2, (255, 255, 0), -1)

                # --- 4e. State Determination & Blink Counter ---
                eye_closed_current = smoothed_ear < self.EYE_AR_THRESH
                eye_status = "Eyes Closed" if eye_closed_current else "Eyes Open"
                status_color = (0, 0, 255) if eye_closed_current else (0, 255, 0)

                # Update Blink Counter
                if not eye_closed_current and self.eye_closed_last_frame:
                    self.blink_count += 1
                self.eye_closed_last_frame = eye_closed_current
                
                # --- 4f. Advanced HUD ---
                cv2.putText(frame, f"State: {eye_status}", (left, bottom + 25), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                cv2.putText(frame, f"Smoothed EAR: {smoothed_ear:.2f}", (left, bottom + 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

                cv2.putText(frame, f"Blinks: {self.blink_count}", (left, bottom + 75), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)

            # 5. Render feed
            cv2.imshow('VisionSight - High Accuracy Bio-Detection', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        print(f"Scanning stopped. Total blinks recorded: {self.blink_count}")

if __name__ == "__main__":
    detector = FaceDetector()
    try:
        detector.run()
    except Exception as e:
        print(f"Biometric Error: {e}")
