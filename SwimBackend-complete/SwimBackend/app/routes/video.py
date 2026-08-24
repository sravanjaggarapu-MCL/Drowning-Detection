# ============================================================
# FILE: video.py
#
# PURPOSE:
# This file contains the FastAPI HTTP routes related to video.
#
# RESPONSIBILITIES:
# - Provide the video service status endpoint.
# - Receive video frames through HTTP.
# - Provide the latest video frame to the frontend.
# - Validate that an uploaded frame exists before processing.
#
# ARCHITECTURE:
#
# Current development:
#
# Test image / Raspberry Pi
#          |
#          | POST /video/frame
#          v
#       FastAPI
#          |
#          v
#    video_service.py
#          |
#          v
#   data/video/latest.jpg
#          |
#          | GET /video/frame
#          v
#       React
#
# IMPORTANT:
# - This file handles HTTP/API concerns only.
# - File storage logic belongs in video_service.py.
# - RTSP camera handling does NOT belong here.
# - YOLO inference does NOT belong here.
# - Raspberry Pi video processing will remain outside this
#   FastAPI route layer.
# ============================================================


from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.video_service import (
    get_latest_frame,
    get_video_status,
    read_latest_frame,
    save_latest_frame,
)


# ============================================================
# ROUTER
# ============================================================
# All routes in this file use the /video prefix.
#
# Therefore:
#
# @router.get("/status")
# becomes:
#
# GET /video/status
# ============================================================

router = APIRouter(
    prefix="/video",
    tags=["Video"]
)


# ============================================================
# GET VIDEO STATUS
# ============================================================

@router.get("/status")
def video_status():
    """
    Return the current status of the video service.

    This endpoint already existed in our backend.
    We are keeping it so existing frontend functionality
    continues to work.
    """

    # Delegate the actual video status logic to the service.
    return get_video_status()


# ============================================================
# POST VIDEO FRAME
# ============================================================

@router.post("/frame")
async def upload_video_frame(
    frame: UploadFile = File(...)
):
    """
    Receive a video frame from a client and save it as
    the latest frame.

    The client sends the image using multipart/form-data.

    Example:

        POST /video/frame

        frame = image.jpg

    The uploaded frame replaces the previous latest frame.
    """

    # Make sure a file was actually selected.
    #
    # FastAPI already requires the field, but this additional
    # check protects the service from an empty filename.
    if not frame.filename:
        raise HTTPException(
            status_code=400,
            detail="No video frame was provided"
        )

    # Read the uploaded image into memory.
    #
    # The result is raw image bytes.
    frame_bytes = await frame.read()

    # Make sure the uploaded file is not empty.
    if not frame_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded video frame is empty"
        )

    # Pass the raw image bytes to the service layer.
    #
    # The route does not know where the file is stored.
    # That responsibility belongs to video_service.py.
    filename = save_latest_frame(
        frame_bytes
    )

    # Return a simple response confirming that the frame
    # was successfully received.
    return {
        "status": "success",
        "filename": filename
    }


# ============================================================
# GET LATEST VIDEO FRAME
# ============================================================

@router.get("/frame")
def get_video_frame():
    """
    Return the latest video frame.

    The frontend can use this endpoint to retrieve the most
    recently received frame.
    """

    # Ask the service layer for the latest frame path.
    frame_path = get_latest_frame()

    # If no frame has been uploaded yet, return 404.
    if frame_path is None:
        raise HTTPException(
            status_code=404,
            detail="No video frame available"
        )

    # Read a stable snapshot before returning. The Raspberry Pi can
    # replace latest.jpg while this request is being served, so a
    # FileResponse for the live path can have a stale Content-Length.
    try:
        frame_bytes = read_latest_frame()
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Latest video frame is temporarily unavailable"
        ) from exc

    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate"
        }
    )