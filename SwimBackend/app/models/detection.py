# ============================================================
# FILE: detection.py
#
# PURPOSE:
# This file defines the database model for detection events.
#
# RESPONSIBILITIES:
# - Define the structure of a detection record in SQLite.
# - Store detection information received from the API.
# - Store the filename of an associated detection image.
#
# IMPORTANT:
# - The actual image file is NOT stored inside SQLite.
# - Images are stored in data/images/.
# - SQLite stores only the image filename.
# - API validation belongs in schemas/detection.py.
# - Business logic belongs in services/detection_service.py.
# ============================================================

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class used by SQLAlchemy database models.

    SQLAlchemy uses this class to discover and create
    database tables.
    """

    pass


class Detection(Base):
    """
    Database model representing one detection event.
    """

    # Name of the SQLite database table.
    __tablename__ = "detections"

    # Unique ID automatically generated for each detection.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    # Identifier of the device that generated the event.
    device_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )

    # Type of event detected by the computer vision system.
    event_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )

    # Confidence score produced by the detection model.
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Time at which the detection occurred.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True
    )

    # Filename of the image associated with this detection.
    #
    # This is optional because a detection does not always
    # have to contain an image.
    image_filename: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )