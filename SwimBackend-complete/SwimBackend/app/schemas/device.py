# ============================================================
# FILE: device.py (schemas)
#
# PURPOSE:
# This file defines the data structures used by the device
# (rescue mechanism) APIs.
#
# RESPONSIBILITIES:
# - Define the structure of the device status response.
# - Define the structure of the emergency rescue request
#   and response.
# - Keep the device API data structures consistent.
#
# IMPORTANT:
# - MQTT communication belongs in services/mqtt_service.py.
# - API endpoints belong in routes/device.py.
# - Field names use snake_case, matching the API contract.
# ============================================================

from pydantic import BaseModel, Field


class DeviceStatusResponse(BaseModel):
    """
    Structure returned by GET /device/status.
    """

    # Identifier reported by the ESP32, or null when the
    # device has never reported.
    device_id: str | None

    # True when the ESP32 heartbeat is recent.
    online: bool

    # Rescue mechanism state:
    # IDLE, DEPLOYING, RETURNING, ERROR, UNKNOWN.
    state: str

    # ISO time of the last ESP32 status message, or null.
    last_seen: str | None

    # Human-readable explanation of the status.
    message: str


class EmergencyRequest(BaseModel):
    """
    Optional body for POST /device/emergency.
    """

    # Why the rescue is being triggered. The dashboard sends
    # "manual"; the detection pipeline uses "auto:...".
    reason: str = Field(
        default="manual",
        description="Reason the rescue deployment was requested"
    )


class EmergencyResponse(BaseModel):
    """
    Structure returned by POST /device/emergency.
    """

    # "accepted" when the command was sent to the device.
    status: str

    # Human-readable result description.
    message: str
