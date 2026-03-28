import cv2

def verify_webcam():
    print("Testing webcam access...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
    
    ret, frame = cap.read()
    if ret:
        print("Success: Webcam captured a frame.")
        cv2.imwrite("verify_webcam.jpg", frame)
        print("Sample frame saved to 'verify_webcam.jpg'.")
    else:
        print("Error: Could not read frame from webcam.")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    verify_webcam()
