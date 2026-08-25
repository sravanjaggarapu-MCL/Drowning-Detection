"""Standalone YOLO inference viewer for webcam or RTSP testing.

This script displays annotated frames only. Use detector.py when
detections must be sent to FastAPI and can trigger MQTT rescue.
"""

from ultralytics import YOLO
import cv2
 
# Path to your trained model
MODEL_PATH = "best (1).pt"
# Load the model
model = YOLO(MODEL_PATH)
 
# Open the default webcam
cap = cv2.VideoCapture(0)
 
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()
 
while True:
    # Read one frame from webcam
    ret, frame = cap.read()
 
    if not ret:
        print("Error: Could not read frame.")
        break
 
    # Run YOLO detection
    results = model(frame, conf=0.5, verbose=False)
 
    # Draw bounding boxes and labels
    annotated_frame = results[0].plot()
 
    # Display the video
    cv2.imshow("YOLO Webcam Detection", annotated_frame)
 
    # Press q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
 
# Release webcam
cap.release()
cv2.destroyAllWindows()