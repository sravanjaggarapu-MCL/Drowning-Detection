# ============================================================
# FILE: detection.py
#
# PURPOSE:
# This file defines the data structures used by the detection
# APIs.
#
# RESPONSIBILITIES:
# - Validate detection information.
# - Define the structure of detection responses.
# - Keep API data structures consistent.
#
# IMPORTANT:
# - Database structure belongs in models/detection.py.
# - Business logic belongs in services/detection_service.py.
# - API endpoints belong in routes/detection.py.
# ============================================================

from datetime import datetime

from pydantic import BaseModel, Field


class DetectionRequest(BaseModel):
    """
    Data structure representing detection information.
    
    This schema is still useful for internal validation and
    future JSON-based requests.
    """

    # Identifier of the device that generated the event.
    device_id: str = Field(
        ...,
        description="Identifier of the device that detected the event"
    )

    # Type of event detected by the computer vision system.
    event_type: str = Field(
        ...,
        description="Type of detection event"
    )

    # Confidence score produced by the detection model.
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0 and 1"
    )

    # Time at which the detection occurred.
    timestamp: datetime = Field(
        ...,
        description="Time when the detection occurred"
    )


class DetectionResponse(BaseModel):
    """
    Structure returned by the backend for a detection event.
    """

    # Unique database ID.
    id: int

    # Device that generated the detection.
    device_id: str

    # Type of detection event.
    event_type: str

    # Model confidence score.
    confidence: float

    # Time at which the detection occurred.
    timestamp: datetime

    # Name of the associated image file, if one exists.
    image_filename: str | None = None

    # Allow Pydantic to create this response directly
    # from a SQLAlchemy model object.
    model_config = {
        "from_attributes": True
    }