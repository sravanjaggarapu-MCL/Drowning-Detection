# ============================================================
# FILE: detector.py
#
# PROJECT: Swimming Pool Drowning Detection (PoolGuard)
#
# PURPOSE:
# Detection client (laptop now, Raspberry Pi later). Reads
# video from a webcam or RTSP camera, runs the CUSTOM-TRAINED
# YOLO model (best (1).pt), and reports to the FastAPI
# backend over HTTP. Runs headless: the dashboard is the
# only video viewer.
#
# RESPONSIBILITIES:
# - Capture frames from the webcam / RTSP stream.
# - Run the custom YOLO model (classes: drowning, swimming,
#   person_out_of_water).
# - Stream annotated frames to the backend (POST /video/frame)
#   so the dashboard live view shows what YOLO sees.
# - Save ONLY confirmed DROWNING events to the database
#   (POST /detection, with the evidence image).
#
# ARCHITECTURE:
#
# Camera ──► this script
#              |
#         custom YOLO ("best (1).pt")
#              |
#    ┌─────────┴───────────────────────────┐
#    | every frame                          | only confirmed
#    | POST /video/frame                    | DROWNING events
#    v                                      v
# FastAPI ──► dashboard live view       POST /detection
#                                           |
#                                FastAPI ──► SQLite + image
#                                           |
#                              (DROWNING ≥ 0.85 auto-triggers
#                               the ESP32 rescue rod via MQTT)
#
# EVENT POLICY (agreed in chat):
# - SWIMMING / PERSON_OUT_OF_WATER are shown on the video
#   overlay but are NOT written to the database.
# - DROWNING is written to the database (which also arms the
#   backend auto-rescue) only after it has been seen
#   continuously for DROWNING_CONFIRM_SECONDS. A single
#   false-positive frame must never move the rescue rod.
#
# MODEL-CLASS → API-EVENT MAPPING:
# The model's own label names (drowning / swimming /
# person_out_of_water) are drawn on the video exactly as
# trained. For the API, they are mapped to the contract
# event types (section 8), which must stay stable:
#     drowning             → DROWNING
#     swimming             → SWIMMING
#     person_out_of_water  → PERSON_DETECTED
#
# RUN:
#   python detector.py                     (laptop webcam)
#   python detector.py --rtsp rtsp://...   (IP camera)
#   python detector.py --mock              (no camera/model)
#   Stop with Ctrl+C.
# ============================================================
 
import argparse
import io
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
 
# Seconds between annotated frames pushed to /video/frame.
# Uploading runs on its own thread so it never blocks YOLO.
FRAME_UPLOAD_INTERVAL = 0.1
 
# Minimum seconds between two DROWNING rows in the database,
# so one long incident does not create dozens of rows.
# (The backend additionally has its own 30 s rescue cooldown.)
DETECTION_INTERVAL = 5.0
 
# YOLO confidence below this is ignored entirely.
MIN_CONFIDENCE = 0.5
 
# ------------------------------------------------------------
# DROWNING CONFIRMATION WINDOW
# ------------------------------------------------------------
# The model must report drowning CONTINUOUSLY for this many
# seconds before the event is sent to the backend. This is
# the safety layer between "one weird frame" and "physically
# deploy the rescue rod". Gaps longer than
# DROWNING_RESET_SECONDS reset the timer.
# ------------------------------------------------------------
DROWNING_CONFIRM_SECONDS = 2.0
DROWNING_RESET_SECONDS = 1.0
 
 
# ============================================================
# MODEL-CLASS → API-EVENT MAPPING
# ============================================================
 
def map_class_to_event(class_name: str) -> str:
    """
    Translate a model label (as trained) into a contract
    event type.
 
    Matching is by substring so small naming differences in
    the trained model ("Drowning", "person out of water",
    "person_out_of_water") all map correctly.
    """
 
    # Normalize: lowercase, unify separators.
    name = class_name.strip().lower().replace(" ", "_").replace("-", "_")
 
    if "drown" in name:
        return EVENT_DROWNING
 
    if "swim" in name:
        return EVENT_SWIMMING
 
    # person_out_of_water and any other person-like class.
    return EVENT_PERSON
 
 
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
 
        Per the agreed event policy, the detector only calls
        this for confirmed DROWNING events, so every row in
        the database is a drowning incident with evidence.
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
 
        # Attach the annotated frame as the evidence image.
        files = None
        if jpeg_bytes is not None:
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
# REAL DETECTION LOOP (webcam / RTSP + custom YOLO)
# ============================================================
 
def run_real(api_url: str, camera_source, model_path: str):
    """
    Full pipeline:
    capture (thread) → YOLO (main) → upload (thread)
    """
 
    # Imported here so mock mode works without these
    # heavy packages installed.
    import cv2
    from ultralytics import YOLO
 
    backend = BackendClient(api_url)
 
    # Load the CUSTOM model trained on pool classes.
    print(f"[yolo] Loading model: {model_path}")
    model = YOLO(model_path)
 
    # Print the model's own classes and how each maps to the
    # API, so a wrong mapping is visible immediately at start.
    print("[yolo] Model classes -> API events:")
    for class_id, class_name in model.names.items():
        print(f"        {class_id}: {class_name} -> "
              f"{map_class_to_event(class_name)}")
 
    # Open the local webcam by default; RTSP when provided.
    source_name = (
        "default laptop camera"
        if isinstance(camera_source, int)
        else camera_source
    )
    print(f"[camera] Opening source: {source_name}")
    capture = cv2.VideoCapture(camera_source)
 
    if not capture.isOpened():
        raise RuntimeError(
            "Could not open the camera source. Check the webcam "
            "index, RTSP URL, or camera connection."
        )
 
    print("[run] Detection running. View the video on the "
          "dashboard. Stop with Ctrl+C.")
 
    # --------------------------------------------------------
    # SHARED STATE BETWEEN THREADS
    # --------------------------------------------------------
 
    latest_frame = None            # newest raw camera frame
    latest_annotated = None        # newest YOLO-annotated frame
    frame_lock = threading.Lock()
    stop_event = threading.Event()
 
    # Drowning confirmation tracking.
    drowning_started_at = None     # when the current streak began
    drowning_last_seen = 0.0       # last time drowning was seen
    last_drowning_post = 0.0       # last time a row was written
 
    # ---- Capture thread: always keep the newest frame ------
    def capture_frames():
        nonlocal latest_frame
 
        while not stop_event.is_set():
            ok, captured = capture.read()
            if not ok:
                print("[camera] Frame read failed, retrying...")
                time.sleep(1.0)
                continue
 
            with frame_lock:
                latest_frame = captured
 
    # ---- Upload thread: stream annotated frames ------------
    def upload_frames():
        while not stop_event.wait(FRAME_UPLOAD_INTERVAL):
            with frame_lock:
                frame_to_upload = latest_annotated
 
            if frame_to_upload is None:
                continue
 
            ok, encoded = cv2.imencode(".jpg", frame_to_upload)
            if not ok:
                continue
 
            try:
                backend.post_frame(encoded.tobytes())
            except Exception as exc:
                print(f"[frame] Upload failed: {exc}")
 
    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=upload_frames, daemon=True).start()
 
    # --------------------------------------------------------
    # MAIN LOOP: YOLO + drowning confirmation
    # --------------------------------------------------------
 
    try:
        while True:
 
            with frame_lock:
                frame = latest_frame
 
            if frame is None:
                time.sleep(0.01)
                continue
 
            now = time.time()
 
            # Run the custom model on the frame.
            #
            # NOTE: no classes=[...] filter here. That filter
            # was for the stock COCO model (0 = person). The
            # custom model's classes ARE our events, so every
            # class must come through.
            results = model.predict(
                frame,
                conf=MIN_CONFIDENCE,
                verbose=False
            )
 
            # Annotate with the model's own labels/colors —
            # the fast built-in renderer keeps the dashboard
            # feed smooth.
            annotated = results[0].plot()
 
            # ---- Scan detections for drowning --------------
            drowning_seen = False
            drowning_confidence = 0.0
 
            for det in results[0].boxes:
 
                confidence = float(det.conf[0])
                class_name = model.names[int(det.cls[0])]
                event_type = map_class_to_event(class_name)
 
                # Only DROWNING matters for the database; the
                # other classes stay visual-only by design.
                if event_type == EVENT_DROWNING:
                    drowning_seen = True
                    drowning_confidence = max(
                        drowning_confidence, confidence
                    )
 
            # ---- Drowning confirmation window --------------
            if drowning_seen:
 
                drowning_last_seen = now
 
                # Start (or continue) the confirmation streak.
                if drowning_started_at is None:
                    drowning_started_at = now
                    print("[drowning] Possible drowning - "
                          f"confirming for {DROWNING_CONFIRM_SECONDS}s...")
 
                streak = now - drowning_started_at
                confirmed = streak >= DROWNING_CONFIRM_SECONDS
                rate_ok = (now - last_drowning_post) >= DETECTION_INTERVAL
 
                if confirmed and rate_ok:
 
                    # Encode the annotated frame as evidence.
                    ok, encoded = cv2.imencode(".jpg", annotated)
                    evidence = encoded.tobytes() if ok else None
 
                    try:
                        # This row can auto-deploy the rescue
                        # rod (backend threshold 0.85).
                        backend.post_detection(
                            EVENT_DROWNING,
                            drowning_confidence,
                            evidence
                        )
                        last_drowning_post = now
                    except Exception as exc:
                        print(f"[detect] POST failed: {exc}")
 
            else:
                # Reset the streak only after a real gap, so a
                # single missed frame doesn't restart the clock.
                if (drowning_started_at is not None and
                        now - drowning_last_seen > DROWNING_RESET_SECONDS):
                    drowning_started_at = None
                    print("[drowning] Cleared - streak reset")
 
            # ---- Publish the annotated frame ----------------
            with frame_lock:
                latest_annotated = annotated
 
    except KeyboardInterrupt:
        print("\n[run] Stopping.")
 
    finally:
        stop_event.set()
        capture.release()
 
 
# ============================================================
# ENTRY POINT
# ============================================================
 
def main():
 
    parser = argparse.ArgumentParser(
        description="PoolGuard detection client"
    )
 
    parser.add_argument(
        "--api",
        default=DEFAULT_API_URL,
        help="FastAPI backend base URL"
    )
 
    parser.add_argument(
        "--rtsp",
        default=None,
        help="Optional RTSP URL; if omitted, the laptop webcam is used"
    )
 
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Webcam index when no RTSP URL is supplied (default: 0)"
    )
 
    parser.add_argument(
        "--model",
        default="best (1).pt",
        help="Custom-trained YOLO model file"
    )
 
    args = parser.parse_args()

    camera_source = args.rtsp if args.rtsp else args.camera
    run_real(args.api, camera_source, args.model)
 
 
if __name__ == "__main__":
    main()