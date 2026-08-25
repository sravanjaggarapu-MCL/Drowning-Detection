# ============================================================
# FILE: mqtt_service.py
#
# PURPOSE:
# This file contains all MQTT communication between the
# PoolGuard backend and the ESP32 rescue device.
#
# RESPONSIBILITIES:
# - Connect to the MQTT broker.
# - Publish rescue commands to the ESP32.
# - Listen to ESP32 status messages.
# - Track whether the rescue device is online.
# - Enforce a cooldown so the rescue mechanism is not
#   triggered repeatedly for the same event.
#
# ARCHITECTURE:
#
# React ──HTTP──► FastAPI (routes/device.py)
#                     |
#                     v
#               mqtt_service.py
#                     |
#                     | MQTT (poolguard/rescue/command)
#                     v
#                  ESP32 ──► L298N ──► DC motor ──► Net rod
#                     |
#                     | MQTT (poolguard/rescue/status)
#                     v
#               mqtt_service.py (status cache)
#
# HARDWARE NOTE:
# The rescue device is a motorized rod with a net that pushes
# a drowning person from the lowest point of the pool up to
# the surface, then returns to its original position.
# There is NO pump, NO valve, NO buzzer, and NO water-level
# sensor in this project.
#
# IMPORTANT:
# - This file does NOT define FastAPI routes.
#   HTTP endpoints belong in routes/device.py.
# - MQTT broker addresses/topics live here in the backend,
#   NEVER in the React frontend (contract sections 16/17).
# - If the broker is unavailable, the backend keeps working;
#   only device features are reported as unavailable.
# ============================================================

import json
import os
import threading
import uuid
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt


# ============================================================
# CONFIGURATION
# ============================================================
# Values can be overridden with environment variables so the
# broker location is not hardcoded for every machine.
#
# During development, run a local Mosquitto broker:
#
#   mosquitto -p 1883
# ============================================================

# Address of the MQTT broker.
MQTT_HOST = os.getenv("POOLGUARD_MQTT_HOST", "127.0.0.1")

# Port of the MQTT broker (1883 is the MQTT default).
MQTT_PORT = int(os.getenv("POOLGUARD_MQTT_PORT", "1883"))

# Topic the backend publishes rescue commands to.
COMMAND_TOPIC = "poolguard/rescue/command"

# Topic the ESP32 publishes its status to.
STATUS_TOPIC = "poolguard/rescue/status"

# The ESP32 is considered offline when no status message has
# been received within this many seconds.
DEVICE_TIMEOUT_SECONDS = 15

# Minimum time between two rescue deployments.
#
# YOLO can produce several DROWNING detections per second for
# the same person. Without a cooldown, the rod would be
# commanded again while it is still deploying/returning.
RESCUE_COOLDOWN_SECONDS = 30


# ============================================================
# INTERNAL STATE
# ============================================================
# The MQTT callbacks run on a background network thread while
# FastAPI handles HTTP requests on other threads, so shared
# state is protected with a lock.
# ============================================================

_client: mqtt.Client | None = None

# Protects the shared state below.
_lock = threading.Lock()

# True while the client is connected to the broker.
_broker_connected = False

# Last status payload received from the ESP32.
_last_device_status: dict | None = None

# Time the last status message arrived.
_last_status_time: datetime | None = None

# Time of the last accepted rescue deployment.
_last_rescue_time: datetime | None = None


# ============================================================
# MQTT CALLBACKS
# ============================================================

def _on_connect(client, userdata, flags, reason_code, properties):
    """
    Called by paho-mqtt when the broker connection is made.
    """

    global _broker_connected

    with _lock:
        _broker_connected = (reason_code == 0)

    # Subscribe to the ESP32 status topic so the backend
    # always knows the current device state.
    if reason_code == 0:
        client.subscribe(STATUS_TOPIC)


def _on_disconnect(client, userdata, flags, reason_code, properties):
    """
    Called when the broker connection is lost.

    paho-mqtt will keep retrying in the background, so no
    manual reconnect logic is needed here.
    """

    global _broker_connected

    with _lock:
        _broker_connected = False


def _on_message(client, userdata, message):
    """
    Called for every MQTT message on a subscribed topic.

    Expected ESP32 status payload (JSON):

    {
        "device_id": "esp32-rescue-01",
        "state": "IDLE"
    }

    States: IDLE, DEPLOYING, RETURNING, ERROR
    """

    global _last_device_status, _last_status_time

    try:
        # Decode the JSON status published by the ESP32.
        payload = json.loads(message.payload.decode("utf-8"))

    except (ValueError, UnicodeDecodeError):
        # Ignore malformed messages instead of crashing the
        # MQTT thread.
        return

    with _lock:
        _last_device_status = payload
        _last_status_time = datetime.now()


# ============================================================
# LIFECYCLE
# ============================================================
# start_mqtt() / stop_mqtt() are called by main.py when the
# FastAPI application starts and shuts down.
# ============================================================

def start_mqtt():
    """
    Connect to the MQTT broker in the background.

    connect_async + loop_start means FastAPI starts normally
    even when the broker is not running yet; paho keeps
    retrying until the broker appears.
    """

    global _client

    # Create the MQTT client (paho-mqtt 2.x callback API).
    _client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"poolguard-backend-{uuid.uuid4().hex[:8]}"
    )

    # Register the callbacks defined above.
    _client.on_connect = _on_connect
    _client.on_disconnect = _on_disconnect
    _client.on_message = _on_message

    # Connect without blocking FastAPI startup.
    _client.connect_async(MQTT_HOST, MQTT_PORT)

    # Start the background network thread.
    _client.loop_start()


def stop_mqtt():
    """
    Disconnect cleanly when FastAPI shuts down.
    """

    global _client

    if _client is not None:
        _client.loop_stop()
        _client.disconnect()
        _client = None


# ============================================================
# DEVICE STATUS
# ============================================================

def get_device_status() -> dict:
    """
    Return the current rescue-device status for the API.

    The device is "online" only when a status message has
    been received recently (heartbeats arrive every few
    seconds from the ESP32).
    """

    with _lock:
        broker_connected = _broker_connected
        status = _last_device_status
        status_time = _last_status_time

    # No broker connection means no device communication.
    if not broker_connected:
        return {
            "device_id": None,
            "online": False,
            "state": "UNKNOWN",
            "last_seen": None,
            "message": "MQTT broker is not connected"
        }

    # Broker is up, but the ESP32 has never reported.
    if status is None or status_time is None:
        return {
            "device_id": None,
            "online": False,
            "state": "UNKNOWN",
            "last_seen": None,
            "message": "No status received from the rescue device yet"
        }

    # Decide freshness: an old heartbeat means the ESP32
    # dropped off the network.
    age = datetime.now() - status_time
    online = age < timedelta(seconds=DEVICE_TIMEOUT_SECONDS)

    return {
        "device_id": status.get("device_id"),
        "online": online,
        "state": status.get("state", "UNKNOWN") if online else "UNKNOWN",
        "last_seen": status_time.isoformat(timespec="seconds"),
        "message": (
            "Rescue device is online"
            if online
            else "Rescue device stopped responding"
        )
    }


# ============================================================
# TRIGGER RESCUE
# ============================================================

def trigger_rescue(reason: str) -> dict:
    """
    Publish a rescue deployment command to the ESP32.

    Args:
        reason:
            Why the rescue was triggered, for example
            "manual" (dashboard button) or
            "auto:DROWNING:0.93" (detection pipeline).

    Returns:
        A dict describing whether the command was accepted:

        {
            "accepted": bool,
            "message": str
        }
    """

    global _last_rescue_time

    with _lock:
        broker_connected = _broker_connected

        # Enforce the cooldown so repeated DROWNING frames do
        # not re-trigger the rod while it is already moving.
        if _last_rescue_time is not None:

            since_last = datetime.now() - _last_rescue_time

            if since_last < timedelta(seconds=RESCUE_COOLDOWN_SECONDS):

                remaining = RESCUE_COOLDOWN_SECONDS - int(
                    since_last.total_seconds()
                )

                return {
                    "accepted": False,
                    "message": (
                        "Rescue already triggered recently. "
                        f"Cooldown: {remaining}s remaining."
                    )
                }

    # Without a broker connection the command cannot reach
    # the ESP32, so the caller must report an error.
    if not broker_connected or _client is None:
        return {
            "accepted": False,
            "message": "MQTT broker is not connected"
        }

    # Build the command payload for the ESP32.
    command = {
        "action": "DEPLOY_RESCUE",
        "reason": reason,

        # Unique id so the ESP32/logs can correlate commands.
        "request_id": uuid.uuid4().hex,

        "timestamp": datetime.now().isoformat(timespec="seconds")
    }

    # Publish with QoS 1 so the broker confirms delivery.
    result = _client.publish(
        COMMAND_TOPIC,
        json.dumps(command),
        qos=1
    )

    # MQTT_ERR_SUCCESS means the message was queued for send.
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        return {
            "accepted": False,
            "message": f"MQTT publish failed (rc={result.rc})"
        }

    # Record the trigger time for the cooldown.
    with _lock:
        _last_rescue_time = datetime.now()

    return {
        "accepted": True,
        "message": "Rescue deployment command sent"
    }
