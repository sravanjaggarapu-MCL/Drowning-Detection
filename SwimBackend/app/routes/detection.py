# ============================================================
# FILE: detection.py
#
# PURPOSE:
# This file defines the HTTP API endpoints for detection events.
#
# RESPONSIBILITIES:
# - Receive detection information through HTTP.
# - Optionally receive a detection image.
# - Retrieve detection history.
# - Retrieve the latest detection.
# - Pass operations to the service layer.
#
# IMPORTANT:
# - Business logic does NOT belong here.
# - Database queries do NOT belong here.
# - Image processing/storage logic belongs in the service layer.
# ============================================================

from datetime import datetime
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile
)
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.detection import (
    DetectionRequest,
    DetectionResponse
)
from app.services.detection_service import (
    get_all_detections,
    get_latest_detection,
    process_detection
)


# Create a router specifically for detection-related APIs.
router = APIRouter(
    prefix="/detection",
    tags=["Detection"]
)


@router.post(
    "",
    response_model=DetectionResponse
)
async def create_detection(
    device_id: str = Form(...),
    event_type: str = Form(...),
    confidence: float = Form(...),
    timestamp: datetime = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    """
    Receive and store a detection event.

    The request uses multipart/form-data because it can contain
    both normal detection fields and an image file.

    The image is optional.
    """

    # Create the same Pydantic detection object used throughout
    # the service layer.
    detection = DetectionRequest(
        device_id=device_id,
        event_type=event_type,
        confidence=confidence,
        timestamp=timestamp
    )

    # Read the uploaded image into memory only when an image
    # was actually provided.
    image_bytes = None
    original_filename = None

    if image is not None:
        # Read the uploaded file contents.
        image_bytes = await image.read()

        # Keep the original filename so we can preserve its
        # file extension when generating our unique filename.
        original_filename = image.filename

    # Pass the validated data and optional image to the service.
    stored_detection = process_detection(
        detection=detection,
        db=db,
        image_bytes=image_bytes,
        original_filename=original_filename
    )

    # FastAPI converts the SQLAlchemy object into the
    # DetectionResponse schema.
    return stored_detection


@router.get(
    "",
    response_model=List[DetectionResponse]
)
def get_detections(
    db: Session = Depends(get_db)
):
    """
    Return all detection events from newest to oldest.
    """

    # Delegate the database operation to the service layer.
    return get_all_detections(db)


@router.get(
    "/latest",
    response_model=DetectionResponse
)
def get_latest(
    db: Session = Depends(get_db)
):
    """
    Return the most recent detection event.
    """

    # Ask the service layer for the latest record.
    latest_detection = get_latest_detection(db)

    # Return 404 when no detection has been recorded yet.
    if latest_detection is None:
        raise HTTPException(
            status_code=404,
            detail="No detection events found"
        )

    return latest_detection


@router.get("/image/{filename}")
def get_detection_image(filename: str):
    """
    Return a saved detection image.

    The frontend can use this endpoint to display an image
    associated with a detection event.
    """

    # Import the image directory from the service layer.
    from app.services.detection_service import IMAGE_DIRECTORY

    # Build the requested image path.
    image_path = IMAGE_DIRECTORY / filename

    # Make sure the requested file actually exists.
    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Detection image not found"
        )

    # Return the image file to the client.
    return FileResponse(image_path)