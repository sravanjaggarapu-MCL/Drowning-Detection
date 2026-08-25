# PoolGuard — Device API Contract Addendum

**Project:** Swimming Pool Drowning Detection
**Status:** Proposed addition to the main API contract (section 19 "Future API Areas"). Per section 5 of the main contract, both developers must agree to this before it is considered final.

---

## 1. Hardware Update (replaces pump/valve/buzzer plans)

The rescue hardware is a **motorized rod with an attached net**:

- On deployment, a DC motor (driven by an **L298N module** connected to the **ESP32**) pushes the rod so the net lifts/pushes the drowning person from the lowest point of the pool to the surface.
- After a short pause at the surface, the rod automatically **returns to its original position**.
- There is **no drain pump, no valve, no buzzer, no strobe, and no water-level sensor**.

The endpoints `POST /device/pump`, `POST /device/valve`, and `POST /device/buzzer` listed in section 19 of the main contract are therefore **cancelled**. They are replaced by the two endpoints below.

The vision device may be a **Raspberry Pi 4 or 5** — the detection client is pure Python and runs on both.

---

## 2. New Endpoints

| Method | Endpoint            | Purpose                              | Status |
|--------|---------------------|--------------------------------------|--------|
| GET    | /device/status      | Current rescue device status         | READY  |
| POST   | /device/emergency   | Deploy the rescue mechanism          | READY  |

### 2.1 GET /device/status

The frontend must use this response rather than assuming the device is connected (same rule as `GET /video/status`).

Response `200 OK`:

```json
{
  "device_id": "esp32-rescue-01",
  "online": true,
  "state": "IDLE",
  "last_seen": "2026-08-22T15:00:00",
  "message": "Rescue device is online"
}
```

Field rules:

- `state` values: `IDLE`, `DEPLOYING`, `RETURNING`, `ERROR`, `UNKNOWN`. These API values must remain stable; the frontend may translate them into friendly labels.
- `online` is `true` only when the ESP32 heartbeat was received within the last 15 seconds.
- `device_id` and `last_seen` are `null` when the device has never reported.

### 2.2 POST /device/emergency

Deploys the rescue rod. The ESP32 performs the full motion cycle (deploy → pause at surface → return) on its own; no second API call is needed.

Optional JSON body:

```json
{ "reason": "manual" }
```

`reason` defaults to `"manual"`. The backend's automatic trigger uses `"auto:DROWNING:<confidence>:id=<detection_id>"` so logs are traceable.

Response `200 OK`:

```json
{ "status": "accepted", "message": "Rescue deployment command sent" }
```

Error responses (extends the status table in main-contract section 13):

| Status | Meaning |
|--------|---------|
| 429    | Rejected: a rescue was triggered within the last 30 seconds (cooldown) |
| 503    | MQTT broker/device communication unavailable |

---

## 3. Automatic Rescue Rule (backend business logic)

When `POST /detection` stores an event with:

- `event_type = "DROWNING"`, and
- `confidence >= 0.85`

the backend automatically publishes the rescue command. Rules:

1. The detection is **always stored first**; an MQTT failure never loses the event.
2. A **30-second cooldown** prevents repeated YOLO frames from re-triggering the rod mid-motion.
3. The threshold `0.85` lives in `app/services/detection_service.py` and can be tuned after real YOLO testing.

---

## 4. MQTT Topics (backend/device layer only — never in React)

| Topic                      | Direction        | Payload |
|----------------------------|------------------|---------|
| `poolguard/rescue/command` | Backend → ESP32  | `{"action":"DEPLOY_RESCUE","reason":"...","request_id":"...","timestamp":"..."}` |
| `poolguard/rescue/status`  | ESP32 → Backend  | `{"device_id":"esp32-rescue-01","state":"IDLE"}` — published on every state change **and** as a heartbeat every 5 seconds |

Broker: Mosquitto on the development laptop, port 1883. Configurable in the backend via `POOLGUARD_MQTT_HOST` / `POOLGUARD_MQTT_PORT` environment variables.

Per main-contract sections 16–17, these topics and the broker address exist only in the backend and device code. React only calls the HTTP endpoints.

---

## 5. Development / Testing Without Hardware

```
Terminal 1:  mosquitto -p 1883
Terminal 2:  cd SwimBackend && uvicorn app.main:app --reload --port 8000
Terminal 3:  cd SwimBackend && python tools/esp32_simulator.py
Terminal 4:  cd pool-drowning-dashboard && npm run dev
Optional  :  cd raspberry_pi && python detector.py --mock
```

- The **ESP32 simulator** behaves exactly like the firmware (same topics, payloads, heartbeat, and deploy → return timing), so the dashboard's Rescue System panel works end-to-end with zero hardware.
- The **Pi client's `--mock` mode** generates fake frames plus periodic detections, including a high-confidence `DROWNING` every ~30 s that exercises the full auto-rescue chain: detection → database → MQTT → (simulated) rod motion → dashboard status.

Manual test of the emergency endpoint:

```
curl -X POST http://127.0.0.1:8000/device/emergency
```

---

## 6. Firmware Notes (ESP32 + L298N)

- Wiring: GPIO 26 → IN1, GPIO 27 → IN2, GPIO 25 → ENA (PWM), common GND between ESP32 and L298N, separate motor supply into the L298N.
- Motion is currently **time-based** (`DEPLOY_TIME_MS` / `RETURN_TIME_MS` in the firmware) and must be tuned to the rod's real travel.
- **Recommended upgrade:** two limit switches (end stops) so the motor stops on physical position instead of time. This should be agreed as a follow-up hardware change.
- The firmware ignores deploy commands while the rod is moving, as a second safety layer under the backend cooldown.
