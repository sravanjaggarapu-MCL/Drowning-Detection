# PoolGuard Backend (SwimBackend)

FastAPI backend for the Swimming Pool Drowning Detection project. Owns the SQLite database, detection images, video frames, all business logic, and the MQTT link to the ESP32 rescue device. Everything else in the system (React dashboard, Raspberry Pi detector) talks to this backend over HTTP; nothing else touches the database or the hardware.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Interactive API docs (Swagger): http://127.0.0.1:8000/docs — you can test every endpoint from the browser here.
- MQTT broker expected at `127.0.0.1:1883` (run `mosquitto -p 1883`). Override with env vars `POOLGUARD_MQTT_HOST` / `POOLGUARD_MQTT_PORT`. The backend still runs if the broker is down; only device features report unavailable.

## Layered Architecture (read code in this order)

```
HTTP request
    │
    ▼
routes/       HTTP concerns only: parse request, call service, return response
    │
    ▼
services/     Business logic: image storage, auto-rescue rule, MQTT, video files
    │
    ▼
models/       SQLAlchemy: database connection + table definitions
    
schemas/      Pydantic: validates API input, shapes API output (sits beside routes)
```

Why the separation matters: routes never contain SQL, services never contain HTTP. Each layer can change (SQLite → PostgreSQL, add an endpoint) without rewriting the others. If you learn one thing from this codebase, learn this pattern.

## Endpoints

| Method | Endpoint                    | Purpose                                   |
|--------|-----------------------------|-------------------------------------------|
| GET    | /health                     | Backend alive check                       |
| GET    | /video/status               | connected / disconnected / error          |
| POST   | /video/frame                | Receive a frame (replaces latest.jpg)     |
| GET    | /video/frame                | Latest frame (dashboard live view)        |
| POST   | /detection                  | Store event + optional image (multipart)  |
| GET    | /detection                  | Full history, newest first                |
| GET    | /detection/latest           | Newest event (404 when none)              |
| GET    | /detection/image/{filename} | Stored evidence image                     |
| GET    | /device/status              | ESP32 rescue rod status                   |
| POST   | /device/emergency           | Deploy the rescue rod (429 cooldown, 503 broker down) |

## Key Business Rules (all in `services/`)

- **Auto-rescue:** `POST /detection` with `event_type=DROWNING` and `confidence >= 0.85` publishes the MQTT deploy command. The event is stored *first* — an MQTT failure can never lose a detection. Threshold: `AUTO_RESCUE_CONFIDENCE_THRESHOLD` in `detection_service.py`.
- **Cooldown:** 30 s between deployments (`mqtt_service.py`), so a burst of DROWNING frames can't re-trigger the rod mid-motion. The firmware also ignores commands while moving (defense in depth).
- **Device presence:** ESP32 heartbeats every 5 s on `poolguard/rescue/status`; silence for 15 s ⇒ reported offline.
- **Images on disk, not in DB:** files go to `data/images/` (frames to `data/video/latest.jpg`); SQLite stores only filenames.

## MQTT Topics (backend/device layer only — never in React)

| Topic                      | Direction       | Payload |
|----------------------------|-----------------|---------|
| poolguard/rescue/command   | backend → ESP32 | `{"action":"DEPLOY_RESCUE","reason":"...","request_id":"...","timestamp":"..."}` |
| poolguard/rescue/status    | ESP32 → backend | `{"device_id":"esp32-rescue-01","state":"IDLE|DEPLOYING|RETURNING|ERROR"}` |

## Testing Without Hardware

`tools/esp32_simulator.py` speaks the exact firmware protocol (same topics, heartbeat, deploy→return timing):

```bash
mosquitto -p 1883                      # terminal 1
uvicorn app.main:app --port 8000       # terminal 2
python tools/esp32_simulator.py        # terminal 3
curl -X POST http://127.0.0.1:8000/device/emergency
```

Watch `/device/status` move IDLE → DEPLOYING → RETURNING → IDLE.

## Why This Stack (short version — full comparison in the root README)

- **FastAPI** over Flask/Django/Express: free validation + Swagger docs, async, and Python matches the YOLO side of the project.
- **SQLite** over PostgreSQL/MongoDB: zero-setup single file; SQLAlchemy makes the future PostgreSQL migration a one-line change.
- **MQTT (Mosquitto)** over HTTP polling/WebSockets: instant push for an emergency command, built-in device presence, the IoT standard.
- **paho-mqtt** is the standard Python MQTT client; nothing else is close.
