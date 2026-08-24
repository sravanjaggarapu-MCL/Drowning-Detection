# ============================================================
# FILE: video_service.py
#
# PURPOSE:
# This file contains the business logic related to video.
#
# RESPONSIBILITIES:
# - Provide the current video service status.
# - Save the latest video frame received by the backend.
# - Retrieve the latest saved video frame.
# - Manage the backend's video-frame storage.
#
# ARCHITECTURE:
#
# Current development:
#
# Test image / future Raspberry Pi
#              |
#              | HTTP
#              v
#           FastAPI
#              |
#              v
#      video_service.py
#              |
#              v
#      data/video/latest.jpg
#              |
#              | HTTP
#              v
#        React Frontend
#
# Future production flow:
#
# IP Camera
#     |
#     | RTSP
#     v
# Raspberry Pi
#     |
#     | Processed video frame
#     v
# FastAPI
#     |
#     v
# React Frontend
#
# IMPORTANT:
# - This file does NOT define FastAPI routes.
# - This file does NOT handle HTTP requests directly.
# - This file does NOT connect to the RTSP camera.
# - This file does NOT run YOLO inference.
# - RTSP/OpenCV/YOLO processing will eventually happen on
#   the Raspberry Pi/video-processing side.
# - The routes in video.py call functions from this file.
#
# STORAGE DESIGN:
# - Only the latest frame is stored.
# - Every new frame replaces the previous latest.jpg.
# - This prevents the backend disk from filling with thousands
#   of individual video frames.
# ============================================================


import os
import tempfile
import threading
from pathlib import Path


# ============================================================
# PROJECT PATH
# ============================================================
# __file__ points to:
#
# FastAPI/app/services/video_service.py
#
# parents[2] takes us back to:
#
# FastAPI/
#
# This gives us a reliable project root regardless of where
# the application is started from.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


# ============================================================
# VIDEO STORAGE DIRECTORY
# ============================================================
# Video frames are stored separately from detection images.
#
# Project structure:
#
# FastAPI/
# └── data/
#     ├── images/
#     └── video/
#         └── latest.jpg
# ============================================================

VIDEO_DIRECTORY = BASE_DIR / "data" / "video"


# ============================================================
# CREATE VIDEO DIRECTORY
# ============================================================
# Create the directory automatically if it does not exist.
#
# parents=True:
# Creates parent directories if necessary.
#
# exist_ok=True:
# Does not raise an error if the directory already exists.
# ============================================================

VIDEO_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LATEST FRAME PATH
# ============================================================
# We intentionally store only one frame.
#
# We do NOT create:
#
# frame1.jpg
# frame2.jpg
# frame3.jpg
# frame4.jpg
# ...
#
# Instead, every new frame overwrites:
#
# data/video/latest.jpg
#
# This is appropriate for our current simple video-frame API.
# ============================================================

LATEST_FRAME_PATH = VIDEO_DIRECTORY / "latest.jpg"
FRAME_FILE_LOCK = threading.Lock()


# ============================================================
# VIDEO STATUS
# ============================================================

def get_video_status():
    """
    Return the current status of the video source.

    API CONTRACT (section 6):
    The response must use one of these status values:

    - "connected"
    - "disconnected"
    - "error"

    together with a human-readable "message".

    CURRENT LOGIC:
    During development there is no real camera yet.
    The video source is considered "connected" when at
    least one frame has been received and saved.

    FUTURE:
    This can be expanded to check frame freshness (file
    modification time) or a real Raspberry Pi heartbeat.
    """

    try:

        # A saved frame means some video source has
        # successfully delivered at least one frame.
        if LATEST_FRAME_PATH.exists():

            return {
                "status": "connected",
                "message": "Video source is available"
            }

        # No frame has ever been received.
        return {
            "status": "disconnected",
            "message": "No video frames have been received yet"
        }

    except OSError as exc:

        # Filesystem problems (permissions, disk errors)
        # are reported as the "error" status.
        return {
            "status": "error",
            "message": f"Video status check failed: {exc}"
        }


# ============================================================
# SAVE LATEST VIDEO FRAME
# ============================================================

def save_latest_frame(frame_bytes: bytes) -> str:
    """
    Save the received video frame as the latest frame.

    Args:
        frame_bytes:
            Raw bytes of the image/frame received by the API.

    Returns:
        The filename of the saved frame.
    """

    # Write to a temporary file in the same directory first. Replacing
    # the completed file atomically prevents readers from seeing a
    # partially written JPEG while a new frame is uploaded.
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=VIDEO_DIRECTORY,
            prefix="latest-",
            suffix=".jpg",
            delete=False
        ) as temporary_file:
            temporary_file.write(frame_bytes)
            temporary_path = Path(temporary_file.name)

        with FRAME_FILE_LOCK:
            os.replace(temporary_path, LATEST_FRAME_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    # Return only the filename instead of exposing the
    # backend's internal filesystem path.
    return LATEST_FRAME_PATH.name


# ============================================================
# GET LATEST VIDEO FRAME
# ============================================================

def get_latest_frame() -> Path | None:
    """
    Return the path of the latest saved video frame.

    Returns:
        Path:
            Path to latest.jpg if a frame exists.

        None:
            If no frame has been received yet.
    """

    # Check whether a frame has been uploaded yet.
    if not LATEST_FRAME_PATH.exists():
        return None

    # Return the filesystem path so the API route can send
    # the image back to the frontend.
    return LATEST_FRAME_PATH


def read_latest_frame() -> bytes:
    """Read one complete frame while uploads are excluded."""

    with FRAME_FILE_LOCK:
        return LATEST_FRAME_PATH.read_bytes()