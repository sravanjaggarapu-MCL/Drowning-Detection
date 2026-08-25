# ============================================================
# FILE: detection_service.py
#
# PURPOSE:
# This file contains the business logic for detection events.
#
# RESPONSIBILITIES:
# - Create and store detection events.
# - Save detection images to disk.
# - Retrieve detection history.
# - Retrieve the latest detection.
# - Automatically trigger the rescue mechanism when a
#   high-confidence DROWNING event is stored.
#
# AUTO-RESCUE ARCHITECTURE:
#
# Raspberry Pi (YOLO) ──POST /detection──► FastAPI
#                                             |
#                                   detection_service.py
#                                             |
#                          DROWNING + high confidence?
#                                             |
#                                     mqtt_service.py
#                                             |
#                                           MQTT
#                                             |
#                              ESP32 ► L298N ► net rod
#
# IMPORTANT:
# - HTTP/API handling belongs in routes/detection.py.
# - Request/response validation belongs in schemas/detection.py.
# - Database structure belongs in models/detection.py.
# - Images are stored on disk, not inside SQLite.
# ============================================================

import uuid
from pathlib import Path

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.detection import Detection
from app.schemas.detection import DetectionRequest


# Find the project root.
#
# __file__ points to:
# FastAPI/app/services/detection_service.py
#
# parents[2] takes us back to:
# FastAPI/
BASE_DIR = Path(__file__).resolve().parents[2]


# Directory where detection images will be stored.
IMAGE_DIRECTORY = BASE_DIR / "data" / "images"


# Create the image directory if it does not already exist.
IMAGE_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# AUTO-RESCUE RULE
# ============================================================
# A DROWNING detection at or above this confidence
# automatically deploys the rescue rod.
#
# Below the threshold, the event is still stored and shown
# on the dashboard, but the hardware is not moved. This
# prevents low-confidence false positives from physically
# activating the mechanism.
#
# The value can be tuned after real YOLO testing.
# ============================================================

AUTO_RESCUE_EVENT = "DROWNING"

AUTO_RESCUE_CONFIDENCE_THRESHOLD = 0.50


def save_detection_image(
    image_bytes: bytes,
    original_filename: str | None
) -> str:
    """
    Save an uploaded detection image to disk.

    Args:
        image_bytes:
            Raw bytes of the uploaded image.

        original_filename:
            Original filename supplied by the client.

    Returns:
        The generated filename used to store the image.
    """

    # Extract the file extension from the original filename.
    # If no filename/extension is provided, use .jpg.
    extension = ".jpg"

    if original_filename:
        suffix = Path(original_filename).suffix.lower()

        if suffix:
            extension = suffix

    # Generate a unique filename so multiple detections
    # cannot accidentally overwrite each other.
    filename = f"{uuid.uuid4().hex}{extension}"

    # Build the complete path where the image will be stored.
    image_path = IMAGE_DIRECTORY / filename

    # Write the image bytes to disk.
    image_path.write_bytes(image_bytes)

    return filename


def process_detection(
    detection: DetectionRequest,
    db: Session,
    image_bytes: bytes | None = None,
    original_filename: str | None = None
):
    """
    Create and store a detection event.

    An image can optionally be associated with the detection.
    """

    # Start with no image associated with the detection.
    image_filename = None

    # Keep evidence images only for drowning events. Other
    # detection types still remain available in the database,
    # but do not create files in data/images.
    if image_bytes and detection.event_type == AUTO_RESCUE_EVENT:
        image_filename = save_detection_image(
            image_bytes,
            original_filename
        )

    # Create the database detection object.
    new_detection = Detection(
        device_id=detection.device_id,
        event_type=detection.event_type,
        confidence=detection.confidence,
        timestamp=detection.timestamp,
        image_filename=image_filename
    )

    # Add the new record to the database transaction.
    db.add(new_detection)

    # Commit the transaction so the detection is persisted.
    db.commit()

    # Refresh the object so SQLAlchemy loads generated values,
    # such as the database ID.
    db.refresh(new_detection)

    # ------------------------------------------------------
    # AUTO-RESCUE TRIGGER
    # ------------------------------------------------------
    # The detection is already safely stored at this point,
    # so a device/MQTT problem can never lose the event.
    # ------------------------------------------------------

    if (
        detection.event_type == AUTO_RESCUE_EVENT
        and detection.confidence >= AUTO_RESCUE_CONFIDENCE_THRESHOLD
    ):

        # Imported here (not at module top) to keep the
        # detection service usable in tests without MQTT.
        from app.services.mqtt_service import trigger_rescue

        # The reason string makes MQTT/ESP32 logs traceable
        # back to the exact detection.
        result = trigger_rescue(
            reason=(
                f"auto:{detection.event_type}"
                f":{detection.confidence}"
                f":id={new_detection.id}"
            )
        )

        # A failed trigger (broker down, cooldown) is logged
        # but does NOT fail the API request: storing the
        # detection must always succeed independently.
        if not result["accepted"]:
            print(
                "[auto-rescue] not deployed:",
                result["message"]
            )

    return new_detection


def get_all_detections(db: Session):
    """
    Retrieve all detection events.

    Results are ordered from newest to oldest.
    """

    # Query all records and sort by timestamp descending.
    detections = (
        db.query(Detection)
        .order_by(desc(Detection.timestamp))
        .all()
    )

    return detections


def get_latest_detection(db: Session):
    """
    Retrieve the most recent detection event.

    Returns None if no detection exists.
    """

    # Retrieve only the newest detection record.
    latest_detection = (
        db.query(Detection)
        .order_by(desc(Detection.timestamp))
        .first()
    )

    return latest_detection