"""Standalone YOLO inference viewer for webcam or RTSP testing.

This script displays annotated frames only. Use detector.py when
detections must be sent to FastAPI and can trigger MQTT rescue.
"""

import argparse
from pathlib import Path

import cv2
from ultralytics import YOLO


MIN_CONFIDENCE = 0.50
WINDOW_TITLE = "PoolGuard YOLO Inference"


def classify_event(box: list[float], frame_height: int) -> str:
    """Match detector.py's current person activity classification."""

    _, _, _, y2 = box
    if y2 > frame_height * 0.6:
        return "SWIMMING"
    return "PERSON_DETECTED"


def annotate_frame(frame, results):
    """Draw person boxes, confidence values, and activity labels."""

    annotated_frame = frame.copy()
    frame_height = frame.shape[0]

    for result in results:
        for detection in result.boxes:
            confidence = float(detection.conf[0])
            box = detection.xyxy[0].tolist()
            x1, y1, x2, y2 = [int(value) for value in box]
            event_type = classify_event(box, frame_height)

            cv2.rectangle(
                annotated_frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )
            cv2.putText(
                annotated_frame,
                f"{event_type} {confidence:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    return annotated_frame


def main():
    parser = argparse.ArgumentParser(
        description="Run PoolGuard YOLO inference on a webcam or RTSP stream."
    )
    parser.add_argument(
        "--model",
        default=str(Path(__file__).with_name("best.pt")),
        help="Path to the YOLO model file."
    )
    parser.add_argument(
        "--rtsp",
        default=None,
        help="RTSP URL. If omitted, the local webcam is used."
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam index when --rtsp is not provided."
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=MIN_CONFIDENCE,
        help="Minimum YOLO confidence, default: 0.50."
    )
    args = parser.parse_args()

    camera_source = args.rtsp if args.rtsp else args.camera
    print(f"[yolo] Loading model: {args.model}")
    model = YOLO(args.model)

    print(f"[camera] Opening source: {camera_source}")
    capture = cv2.VideoCapture(camera_source)
    if not capture.isOpened():
        raise RuntimeError(
            "Could not open the camera source. Check the webcam index or RTSP URL."
        )

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                print("[camera] Frame read failed.")
                break

            results = model.predict(
                frame,
                classes=[0],
                conf=args.conf,
                verbose=False
            )
            annotated_frame = annotate_frame(frame, results)
            cv2.imshow(WINDOW_TITLE, annotated_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()