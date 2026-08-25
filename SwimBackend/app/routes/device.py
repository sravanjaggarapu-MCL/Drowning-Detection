# ============================================================
# FILE: device.py (routes)
#
# PURPOSE:
# This file defines the HTTP API endpoints for the ESP32
# rescue device (motorized net rod).
#
# RESPONSIBILITIES:
# - Report the current rescue-device status to the frontend.
# - Accept an emergency rescue request from the frontend.
# - Pass device operations to the MQTT service layer.
#
# ARCHITECTURE:
#
# React ──HTTP──► routes/device.py ──► mqtt_service.py ──MQTT──► ESP32
#
# ENDPOINTS (contract section 19 / device addendum):
#
# GET  /device/status     → current rescue device status
# POST /device/emergency  → deploy the rescue mechanism
#
# IMPORTANT:
# - React NEVER talks to MQTT or the ESP32 directly
#   (contract sections 16/17). It only calls these endpoints.
# - MQTT logic does NOT belong here; it lives in
#   services/mqtt_service.py.
# - There is no pump, valve, or buzzer endpoint because the
#   hardware uses only the motorized rescue rod.
# ============================================================

from fastapi import APIRouter, HTTPException

from app.schemas.device import (
    DeviceStatusResponse,
    EmergencyRequest,
    EmergencyResponse
)
from app.services.mqtt_service import (
    get_device_status,
    trigger_rescue
)


# Create a router specifically for device-related APIs.
router = APIRouter(
    prefix="/device",
    tags=["Device"]
)


@router.get(
    "/status",
    response_model=DeviceStatusResponse
)
def device_status():
    """
    Return the current status of the rescue device.

    The frontend should use this response rather than
    assuming the device is connected, exactly like the
    video-status rule in contract section 6.
    """

    # The MQTT service tracks the ESP32 heartbeat and state.
    return get_device_status()


@router.post(
    "/emergency",
    response_model=EmergencyResponse
)
def emergency_rescue(
    request: EmergencyRequest | None = None
):
    """
    Deploy the rescue mechanism.

    The ESP32 drives the motorized rod so the net pushes the
    person from the lowest point of the pool to the surface,
    then automatically returns the rod to its start position.

    Responses:
    - 200: command accepted and sent to the device.
    - 429: rejected because a rescue was triggered very
           recently (cooldown).
    - 503: MQTT broker/device communication unavailable.
    """

    # The body is optional; default the reason to "manual".
    reason = request.reason if request else "manual"

    # Ask the MQTT service to publish the deploy command.
    result = trigger_rescue(reason=reason)

    if not result["accepted"]:

        # Cooldown rejections are a client-visible rule,
        # not a server failure.
        if "Cooldown" in result["message"]:
            raise HTTPException(
                status_code=429,
                detail=result["message"]
            )

        # Anything else means the device path is unavailable.
        raise HTTPException(
            status_code=503,
            detail=result["message"]
        )

    return {
        "status": "accepted",
        "message": result["message"]
    }
