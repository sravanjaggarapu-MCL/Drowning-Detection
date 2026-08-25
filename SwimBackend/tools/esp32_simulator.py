# ============================================================
# FILE: esp32_simulator.py
#
# PURPOSE:
# Simulates the ESP32 rescue device over MQTT so the full
# backend/frontend chain can be developed and tested with
# NO hardware connected.
#
# RESPONSIBILITIES:
# - Publish heartbeat status messages like the real ESP32.
# - Listen for rescue commands from the backend.
# - Simulate the deploy → return motion with timed states.
#
# ARCHITECTURE:
#
# FastAPI ──MQTT──► this simulator (pretending to be ESP32)
#                        |
#                 IDLE → DEPLOYING → RETURNING → IDLE
#                        |
# FastAPI ◄──MQTT── status heartbeats
#
# USAGE:
# 1. Start a local broker:    mosquitto -p 1883
# 2. Start the backend:       uvicorn app.main:app --port 8000
# 3. Start this simulator:    python tools/esp32_simulator.py
# 4. Trigger from the dashboard button, or:
#        curl -X POST http://127.0.0.1:8000/device/emergency
#
# IMPORTANT:
# - Topics and payloads here MUST match the real firmware
#   (esp32/poolguard_rescue/poolguard_rescue.ino) and the
#   backend (app/services/mqtt_service.py).
# ============================================================

import json
import threading
import time

import paho.mqtt.client as mqtt


# ============================================================
# CONFIGURATION (must match mqtt_service.py and the firmware)
# ============================================================

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

# Backend → device commands.
COMMAND_TOPIC = "poolguard/rescue/command"

# Device → backend status.
STATUS_TOPIC = "poolguard/rescue/status"

# Identifier reported in every status message.
DEVICE_ID = "esp32-rescue-01"

# Simulated motion timing (the real firmware uses motor
# run-times tuned to the rod's travel distance).
DEPLOY_SECONDS = 4
RETURN_SECONDS = 4

# Heartbeat interval, same as the firmware.
HEARTBEAT_SECONDS = 5


# ============================================================
# STATE
# ============================================================

# Current rescue mechanism state:
# IDLE, DEPLOYING, RETURNING.
state = "IDLE"

# Protects the shared state between threads.
state_lock = threading.Lock()


def publish_status(client):
    """
    Publish the current state exactly like the ESP32 does.
    """

    with state_lock:
        payload = {
            "device_id": DEVICE_ID,
            "state": state
        }

    client.publish(STATUS_TOPIC, json.dumps(payload), qos=1)


def rescue_sequence(client):
    """
    Simulate the physical rescue motion:

    DEPLOYING: the rod pushes the net (and the person) from
               the lowest point of the pool to the surface.
    RETURNING: the rod moves back to its original position.
    """

    global state

    # --- Deploy phase -------------------------------------
    with state_lock:
        state = "DEPLOYING"
    publish_status(client)
    print(f"[sim] DEPLOYING for {DEPLOY_SECONDS}s ...")
    time.sleep(DEPLOY_SECONDS)

    # --- Return phase -------------------------------------
    with state_lock:
        state = "RETURNING"
    publish_status(client)
    print(f"[sim] RETURNING for {RETURN_SECONDS}s ...")
    time.sleep(RETURN_SECONDS)

    # --- Back to rest -------------------------------------
    with state_lock:
        state = "IDLE"
    publish_status(client)
    print("[sim] Rescue complete. Rod back at start position.")


def on_connect(client, userdata, flags, reason_code, properties):
    """
    Subscribe to commands once connected, and announce IDLE.
    """

    print(f"[sim] Connected to broker (rc={reason_code})")
    client.subscribe(COMMAND_TOPIC)
    publish_status(client)


def on_message(client, userdata, message):
    """
    Handle a rescue command from the backend.
    """

    global state

    try:
        command = json.loads(message.payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        print("[sim] Ignored malformed command")
        return

    print(f"[sim] Command received: {command}")

    if command.get("action") == "DEPLOY_RESCUE":

        with state_lock:
            busy = state != "IDLE"

        # The real firmware also ignores commands while the
        # rod is moving; the backend cooldown normally
        # prevents this case anyway.
        if busy:
            print("[sim] Busy - command ignored")
            return

        # Run the motion in a thread so MQTT keeps working.
        threading.Thread(
            target=rescue_sequence,
            args=(client,),
            daemon=True
        ).start()


def main():

    # Create the MQTT client (paho-mqtt 2.x callback API).
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="esp32-simulator"
    )

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()

    print("[sim] ESP32 rescue simulator running. Ctrl+C to stop.")

    # Heartbeat loop, same rhythm as the real firmware.
    try:
        while True:
            time.sleep(HEARTBEAT_SECONDS)
            publish_status(client)

    except KeyboardInterrupt:
        print("\n[sim] Stopping.")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
