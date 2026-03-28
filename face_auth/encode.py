import cv2
import face_recognition
import pickle
import os

class FaceEncoder:
    def __init__(self, known_faces_dir="assets/known_faces"):
        self.known_faces_dir = known_faces_dir
        self.encodings_file = os.path.join(self.known_faces_dir, "encodings.pkl")
        
        # Ensure the directory exists
        if not os.path.exists(self.known_faces_dir):
            os.makedirs(self.known_faces_dir)
            print(f"Created directory: {self.known_faces_dir}")

    def generate_encodings(self):
        """
        Scans the known_faces directory, generates 128-d encodings, 
        and saves them to a pickle file.
        """
        known_encodings = {}
        found_images = False

        print(f"Scanning '{self.known_faces_dir}' for authorized user images...")

        for filename in os.listdir(self.known_faces_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                found_images = True
                image_path = os.path.join(self.known_faces_dir, filename)
                name = os.path.splitext(filename)[0]

                print(f"Processing image for: {name}...")

                # 1. Load image
                image = face_recognition.load_image_file(image_path)
                
                # 2. Get 128-d encoding (High Accuracy Mode: 100 jitters)
                # We assume only ONE face per reference image!
                encodings = face_recognition.face_encodings(image, num_jitters=100, model="large")
                
                if len(encodings) > 0:
                    known_encodings[name] = encodings[0]
                    print(f"Successfully encoded {name}.")
                else:
                    print(f"Warning: No face found in {filename}. Skipping...")

        if not found_images:
            print("\n" + "!"*40)
            print("ERROR: No images found in 'assets/known_faces/'.")
            print("Please add a clear, front-facing photo of yourself to continue.")
            print("!"*40 + "\n")
            return False

        # 3. Save to pickle file
        with open(self.encodings_file, "wb") as f:
            pickle.dump(known_encodings, f)
            print(f"\nSaved {len(known_encodings)} authorized signatures to '{self.encodings_file}'.")
        
        return True

if __name__ == "__main__":
    encoder = FaceEncoder()
    encoder.generate_encodings()
