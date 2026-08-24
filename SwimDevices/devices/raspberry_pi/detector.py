# ============================================================
# FILE: detector.py
#
# PROJECT: Swimming Pool Drowning Detection (PoolGuard)
#
# PURPOSE:
# Raspberry Pi detection client. Reads video from the IP
# camera (RTSP), runs YOLO person detection, and reports
# everything to the FastAPI backend over HTTP.
#
# RESPONSIBILITIES:
# - Capture frames from the RTSP camera stream.
# - Run YOLO person detection on the frames.
# - Classify activity (PERSON_DETECTED / SWIMMING / DROWNING).
# - POST video frames to the backend (POST /video/frame).
# - POST detection events to the backend (POST /detection),
#   including the evidence image.
#
# ARCHITECTURE:
#
# IP Camera ──RTSP──► this script (Raspberry Pi 4 or 5)
#                         |
#                       YOLO
#                         |
#         ┌───────────────┴────────────────┐
#         | POST /video/frame              | POST /detection
#         v                                v
#      FastAPI  ──► data/video/       FastAPI ──► SQLite +
#                   latest.jpg                    data/images/
#                                          |
#                              (DROWNING ≥ 0.85 auto-triggers
#                               the ESP32 rescue rod via MQTT)
#
# IMPORTANT:
# - This script is the ONLY component that touches RTSP/YOLO.
#   The React frontend never sees the camera or the model
#   (contract sections 3 and 15).
# - All API field names are snake_case per the contract.
# - Runs unchanged on Raspberry Pi 4 or 5 (pure Python).
# - MOCK MODE (--mock) runs without a camera or YOLO model,
#   generating synthetic detections for integration testing.
#
# DROWNING HEURISTIC (PLACEHOLDER):
# Real drowning classification needs a trained model or a
# temporal rule (e.g. a person low in the frame and nearly
# motionless for N seconds). The _classify_event() function
# below is a simple placeholder marked clearly for
# replacement — the API contract does not change when the
# logic improves.
#
# INSTALL (on the Pi):
#   pip install -r requirements.txt
#
# RUN:
#   python detector.py --rtsp rtsp://user:pass@CAMERA_IP:554/stream
#   python detector.py --mock          (no camera/model needed)
# ============================================================

import argparse
import io
import random
import threading
import time
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

# FastAPI backend base URL (the laptop during development).
DEFAULT_API_URL = "http://127.0.0.1:8000"

# Identifier sent with every detection (contract section 7).
DEVICE_ID = "raspberry-pi-01"

# Contract event types (section 8). These strings must NEVER
# change without agreement between both developers.
EVENT_DROWNING = "DROWNING"
EVENT_SWIMMING = "SWIMMING"
EVENT_PERSON = "PERSON_DETECTED"

# Seconds between frames pushed to /video/frame. Uploading
# happens independently from YOLO so inference cannot make
# the live view arrive in bursts.
FRAME_UPLOAD_INTERVAL = 0.1

# Minimum seconds between two detection POSTs of the same
# event type, so the database is not flooded with duplicates.
DETECTION_INTERVAL = 5.0

# YOLO confidence below this is ignored entirely.
MIN_CONFIDENCE = 0.5


# ============================================================
# BACKEND CLIENT
# ============================================================
# Small wrapper around the two contract endpoints this
# device uses. Kept separate from the vision logic so the
# HTTP layer can be tested alone.
# ============================================================

class BackendClient:
    """
    Sends frames and detections to the FastAPI backend.
    """

    def __init__(self, api_url: str):

        # Imported here so --help works without the package.
        import requests

        self._requests = requests

        # Base URL without a trailing slash.
        self.api_url = api_url.rstrip("/")

    def post_frame(self, jpeg_bytes: bytes):
        """
        POST /video/frame — replaces the backend's latest.jpg.
        """

        self._requests.post(
            f"{self.api_url}/video/frame",

            # Field name must be "frame" to match the
            # FastAPI parameter (routes/video.py).
            files={
                "frame": ("frame.jpg", jpeg_bytes, "image/jpeg")
            },
            timeout=5
        )

    def post_detection(
        self,
        event_type: str,
        confidence: float,
        jpeg_bytes: bytes | None
    ):
        """
        POST /detection — stores the event (+ evidence image).

        A DROWNING event at/above the backend threshold will
        automatically deploy the rescue rod (backend logic).
        """

        # Contract fields, snake_case (section 7).
        data = {
            "device_id": DEVICE_ID,
            "event_type": event_type,

            # Keep the raw 0.0–1.0 value (section 12).
            "confidence": f"{confidence:.2f}",

            # ISO datetime (section 12).
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            )
        }

        # Only drowning events need an evidence image. Live frames
        # continue through /video/frame without filling data/images.
        files = None
        if jpeg_bytes is not None and event_type == EVENT_DROWNING:
            files = {
                "image": ("evidence.jpg", jpeg_bytes, "image/jpeg")
            }

        response = self._requests.post(
            f"{self.api_url}/detection",
            data=data,
            files=files,
            timeout=10
        )

        print(
            f"[detect] {event_type} ({confidence:.2f}) "
            f"-> HTTP {response.status_code}"
        )


# ============================================================
# EVENT CLASSIFICATION (PLACEHOLDER)
# ============================================================

def _classify_event(box, frame_height: int) -> str:
    """
    Decide the event type for one detected person.

    *** PLACEHOLDER LOGIC — REPLACE WITH REAL RULES ***

    Current simple rule:
    - Person in the lower part of the frame (deep in the
      pool area as seen by an overhead/angled camera)
      → SWIMMING.
    - Otherwise → PERSON_DETECTED.

    DROWNING should come from a real temporal analysis
    (e.g. person submerged/low + minimal movement for
    N seconds) or a custom-trained model. Returning
    DROWNING here would physically move the rescue rod,
    so the placeholder deliberately never returns it.
    """

    # Bottom y-coordinate of the person's bounding box.
    _, _, _, y2 = box

    # Lower 40% of the frame ≈ inside the pool.
    if y2 > frame_height * 0.6:
        return EVENT_SWIMMING

    return EVENT_PERSON


# ============================================================
# REAL DETECTION LOOP (RTSP + YOLO)
# ============================================================

def run_real(api_url: str, camera_source, model_path: str):
    """
    Full pipeline: webcam/RTSP capture → YOLO → backend reporting.
    """

    # Imported here so mock mode works without these
    # heavy packages installed.
    import cv2
    from ultralytics import YOLO

    backend = BackendClient(api_url)

    # Load the YOLO model. "yolov8n.pt" (nano) is the right
    # starting point for a Raspberry Pi 4/5 CPU.
    print(f"[yolo] Loading model: {model_path}")
    model = YOLO(model_path)

    # Open the local webcam by default; RTSP can still be used
    # when explicitly provided.
    source_name = "default laptop camera" if isinstance(camera_source, int) else camera_source
    print(f"[camera] Opening source: {source_name}")
    capture = cv2.VideoCapture(camera_source)

    if not capture.isOpened():
        raise RuntimeError(
            "Could not open the camera source. Check the webcam index, "
            "RTSP URL, or camera connection."
        )

    last_detection_post: dict[str, float] = {}
    latest_frame = None
    frame_lock = threading.Lock()
    stop_event = threading.Event()

    def capture_frames():
        nonlocal latest_frame

        while not stop_event.is_set():
            ok, captured_frame = capture.read()
            if not ok:
                print("[rtsp] Frame read failed, retrying...")
                time.sleep(1.0)
                continue

            with frame_lock:
                latest_frame = captured_frame

    def upload_frames():
        while not stop_event.wait(FRAME_UPLOAD_INTERVAL):
            with frame_lock:
                frame_to_upload = latest_frame

            if frame_to_upload is None:
                continue

            ok, encoded = cv2.imencode(".jpg", frame_to_upload)
            if not ok:
                continue

            try:
                backend.post_frame(encoded.tobytes())
            except Exception as exc:
                print(f"[frame] Upload failed: {exc}")

    capture_thread = threading.Thread(
        target=capture_frames,
        name="camera-capture",
        daemon=True
    )
    upload_thread = threading.Thread(
        target=upload_frames,
        name="frame-uploader",
        daemon=True
    )
    capture_thread.start()
    upload_thread.start()

    try:
        while True:

            with frame_lock:
                frame = latest_frame

            if frame is None:
                time.sleep(0.01)
                continue

            now = time.time()

            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            jpeg_bytes = encoded.tobytes()

            results = model.predict(
                frame,
                classes=[0],
                conf=MIN_CONFIDENCE,
                verbose=False
            )

            frame_height = frame.shape[0]

            for result in results:
                for det in result.boxes:

                    confidence = float(det.conf[0])
                    box = det.xyxy[0].tolist()

                    event_type = _classify_event(box, frame_height)

                    last = last_detection_post.get(event_type, 0.0)
                    if now - last < DETECTION_INTERVAL:
                        continue

                    try:
                        backend.post_detection(
                            event_type,
                            confidence,
                            jpeg_bytes
                        )
                        last_detection_post[event_type] = now
                    except Exception as exc:
                        print(f"[detect] POST failed: {exc}")
    finally:
        stop_event.set()
        capture.release()


# ============================================================
# MOCK MODE (NO CAMERA / NO YOLO)
# ============================================================

def run_mock(api_url: str):
    """
    Integration-test mode: generates synthetic frames and
    detections so the whole backend → MQTT → ESP32 (or
    simulator) → dashboard chain can be tested on a laptop.
    """

    # Pillow draws the fake frames; much lighter than OpenCV.
    from PIL import Image, ImageDraw

    backend = BackendClient(api_url)

    print("[mock] Running WITHOUT camera/YOLO.")
    print("[mock] A DROWNING event fires every ~30s to "
          "exercise the auto-rescue path.")

    counter = 0

    while True:

        counter += 1

        # ---- Build a fake camera frame --------------------
        image = Image.new("RGB", (640, 360), (30, 90, 140))
        draw = ImageDraw.Draw(image)
        draw.text(
            (20, 20),
            f"MOCK POOL FEED  frame={counter}  "
            f"{datetime.now().strftime('%H:%M:%S')}",
            fill=(255, 255, 255)
        )

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        jpeg_bytes = buffer.getvalue()

        # ---- Upload the fake frame ------------------------
        try:
            backend.post_frame(jpeg_bytes)
        except Exception as exc:
            print(f"[mock] Frame upload failed: {exc}")

        # ---- Periodic fake detections ---------------------
        # Every 10th cycle: normal activity.
        # Every 30th cycle: a high-confidence DROWNING, which
        # makes the backend deploy the rescue rod.
        try:
            if counter % 30 == 0:
                backend.post_detection(
                    EVENT_DROWNING,
                    random.uniform(0.88, 0.97),
                    jpeg_bytes
                )
            elif counter % 10 == 0:
                backend.post_detection(
                    random.choice([EVENT_SWIMMING, EVENT_PERSON]),
                    random.uniform(0.60, 0.90),
                    jpeg_bytes
                )
        except Exception as exc:
            print(f"[mock] Detection POST failed: {exc}")

        # One cycle per second, matching the live-view rate.
        time.sleep(1.0)


# ============================================================
# ENTRY POINT
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="PoolGuard Raspberry Pi detection client"
    )

    parser.add_argument(
        "--api",
        default=DEFAULT_API_URL,
        help="FastAPI backend base URL"
    )

    parser.add_argument(
        "--rtsp",
        default=None,
        help="Optional RTSP URL of an IP camera; if omitted, the default laptop webcam is used."
    )

    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam index to use when no RTSP URL is supplied (default: 0)"
    )

    parser.add_argument(
        "--model",
        default="best.pt",
        help="YOLO model file (custom trained model used for this pool detection setup)"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without camera/YOLO (integration testing)"
    )

    args = parser.parse_args()

    if args.mock:
        run_mock(args.api)
        return

    camera_source = args.rtsp if args.rtsp else args.camera
    run_real(args.api, camera_source, args.model)


if __name__ == "__main__":
    main()
