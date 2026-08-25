# PoolGuard
## Frontend ↔ Backend API Contract

**Purpose:** This document is the shared source of truth for frontend and backend development. Both developers should follow the API names, request formats, response fields, naming conventions, and responsibilities defined here.

## 1. Project Goal

PoolGuard is a swimming-pool monitoring system intended to detect important pool events such as drowning/swimming activity, record detection evidence, display the current situation to a user, and eventually communicate with an ESP32-controlled safety system.

```text
IP Camera
   ↓ RTSP
Raspberry Pi
   ↓
YOLO / computer vision
   ↓
FastAPI
   ├── SQLite
   ├── Detection images
   └── MQTT
        ↓
      ESP32
        ↓
Relay / Pump / Valve / Buzzer

React Frontend
   ↓ HTTP
FastAPI
```

## 2. Development Architecture Right Now

The Raspberry Pi and hardware are not required for current backend/frontend development. The laptop-hosted FastAPI server is the integration point, and the frontend communicates with it through HTTP.

```text
React Frontend
      │
      │ HTTP / REST
      ▼
FastAPI Backend
      ├── SQLite
      └── data/images/
```

## 3. Core Architecture Rules

1. React communicates with FastAPI, not directly with SQLite, Raspberry Pi, camera, ESP32, or MQTT.
2. FastAPI owns business logic and communication with internal services/devices.
3. YOLO is an internal computer-vision component. The frontend does not depend on the YOLO implementation.
4. API field names use `snake_case`. Do not change API names to `camelCase` without agreement.
5. Frontend and backend must agree on an API contract before implementing a new feature.
6. If an endpoint or response field must change, tell the other developer before changing it.

## 4. Current API Contract

| Method | Endpoint | Purpose | Status |
|---|---|---|---|
| GET | `/health` | Backend health check | READY |
| GET | `/video/status` | Current video/camera status | READY |
| POST | `/detection` | Create detection with optional image | READY |
| GET | `/detection` | Get detection history | READY |
| GET | `/detection/latest` | Get newest detection | READY |
| GET | `/detection/image/{filename}` | Retrieve saved detection image | READY |
| POST | `/video/frame` | Receive a video frame | NEXT |
| GET | `/video/frame` | Retrieve latest video frame | NEXT |
| POST | `/device/...` | ESP32/device operations | FUTURE |

## 5. GET `/health`

**Purpose:** Confirm that the backend is running.

### Response: `200 OK`

```json
{
  "status": "ok",
  "message": "PoolGuard backend is running"
}
```

## 6. GET `/video/status`

**Purpose:** Report the current video/camera state. The frontend should use the backend response rather than assuming the camera is connected.

### Example response

```json
{
  "status": "connected",
  "message": "Video source is available"
}
```

### Expected status values

- `connected`
- `disconnected`
- `error`

## 7. POST `/detection`

**Purpose:** Create a detection event and optionally save the evidence image. Because an image may be included, the request uses `multipart/form-data`.

### Request fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `device_id` | string | Yes | Device that generated the event |
| `event_type` | string | Yes | Detection event type |
| `confidence` | float | Yes | Model confidence from 0.0 to 1.0 |
| `timestamp` | datetime | Yes | Time the detection occurred |
| `image` | file | No | Evidence image |

### Example request

```text
POST /detection
Content-Type: multipart/form-data

device_id: raspberry-pi-01
event_type: DROWNING
confidence: 0.91
timestamp: 2026-08-22T14:30:00
image: detection.jpg
```

### Response: `200 OK`

```json
{
  "id": 1,
  "device_id": "raspberry-pi-01",
  "event_type": "DROWNING",
  "confidence": 0.91,
  "timestamp": "2026-08-22T14:30:00",
  "image_filename": "8f7a9c123.jpg"
}
```

## 8. Detection Event Types

The initial agreed values are:

- `DROWNING`
- `SWIMMING`
- `PERSON_DETECTED`

The API values must remain stable. The frontend may translate them into friendly labels, icons, or colors.

## 9. GET `/detection`

**Purpose:** Return detection history, newest first.

### Response: `200 OK`

```json
[
  {
    "id": 3,
    "device_id": "raspberry-pi-01",
    "event_type": "DROWNING",
    "confidence": 0.94,
    "timestamp": "2026-08-22T14:35:00",
    "image_filename": "abc.jpg"
  },
  {
    "id": 2,
    "device_id": "raspberry-pi-01",
    "event_type": "SWIMMING",
    "confidence": 0.87,
    "timestamp": "2026-08-22T14:30:00",
    "image_filename": "xyz.jpg"
  }
]
```

## 10. GET `/detection/latest`

**Purpose:** Return the most recent detection event.

### Response: `200 OK`

```json
{
  "id": 3,
  "device_id": "raspberry-pi-01",
  "event_type": "DROWNING",
  "confidence": 0.94,
  "timestamp": "2026-08-22T14:35:00",
  "image_filename": "abc.jpg"
}
```

If no detection exists, the backend returns `404 Not Found`.

## 11. Detection Images

Images are stored on the backend filesystem, not inside SQLite. SQLite stores only the filename.

```text
SQLite
image_filename = "abc.jpg"

Actual file:
data/images/abc.jpg
```

### Retrieve an image

```text
GET /detection/image/abc.jpg
```

The React frontend can use the endpoint as the image source.

## 12. Confidence and Timestamp Rules

- Confidence is stored as a number between `0.0` and `1.0`.
- The frontend may display `0.91` as `91%`, but the API/database should keep `0.91`.
- Timestamps use ISO-style datetime values such as `2026-08-22T14:30:00`.
- The frontend formats the timestamp for display.

## 13. HTTP Status Codes

| Status | Meaning |
|---|---|
| `200` | Request succeeded |
| `201` | Resource created, when used by a future creation endpoint |
| `404` | Requested resource does not exist |
| `422` | Request data failed FastAPI/Pydantic validation |
| `500` | Unexpected server-side error |

## 14. Frontend API Organization

React should keep backend communication in a dedicated API layer rather than placing raw URLs throughout UI components.

```text
frontend/
├── src/
│   ├── api/
│   │   ├── client.js
│   │   ├── detectionApi.js
│   │   └── videoApi.js
│   │
│   ├── components/
│   │   ├── DetectionCard.jsx
│   │   ├── DetectionHistory.jsx
│   │   ├── VideoPlayer.jsx
│   │   └── SystemStatus.jsx
│   │
│   └── pages/
│       └── Dashboard.jsx
```

Use one `API_BASE_URL` configuration value. Do not hardcode `http://127.0.0.1:8000` throughout the application.

## 15. Video Architecture

The IP camera uses RTSP, but the browser frontend should not directly depend on the camera's RTSP URL. The Raspberry Pi/backend layer will eventually provide a browser-compatible stream or frame endpoint.

```text
IP Camera
   ↓ RTSP
Raspberry Pi
   ↓
Video / YOLO processing
   ↓
FastAPI
   ↓ HTTP-compatible video API
React
```

The exact production streaming mechanism (MJPEG, HLS, WebRTC, etc.) should be agreed before the final frontend video component is implemented.

## 16. MQTT / ESP32 Architecture

React must not directly communicate with MQTT or the ESP32. The frontend sends an HTTP request to FastAPI; FastAPI handles MQTT/device communication.

```text
React
   ↓ HTTP
FastAPI
   ↓ MQTT
ESP32
   ↓
Relay / Pump / Valve / Buzzer
```

MQTT broker addresses, topics, credentials, and hardware details belong to the backend/device layer and should not be embedded in React.

## 17. Things We Must NOT Do

- Do not change API field names independently.
- Do not make React connect directly to SQLite.
- Do not make React connect directly to the Raspberry Pi.
- Do not make React connect directly to the ESP32 or MQTT broker.
- Do not expose MQTT topics or credentials in frontend code.
- Do not make the frontend depend on YOLO model names or formats.
- Do not permanently mix mock data with real API calls.
- Do not introduce a new endpoint without first agreeing on its contract.

## 18. Development Workflow

1. Agree on the feature.
2. Define endpoint + method.
3. Define request fields and types.
4. Define response fields and types.
5. Define status/error behavior.
6. Backend implements the contract.
7. Frontend implements against the contract.
8. Test with Swagger/Postman.
9. Integrate React with the real endpoint.
10. Only then move to the next feature.

## 19. Future API Areas

```text
POST /video/frame
GET  /video/frame
GET  /device/status
POST /device/emergency
POST /device/pump
POST /device/valve
POST /device/buzzer
```

Other endpoints should be defined only after their exact request/response contract is agreed by both developers.

## 20. Final Target Architecture

```text
                           POOLGUARD

       IP CAMERA                         React Frontend
           │                                  │
          RTSP                               HTTP
           │                                  │
           ▼                                  ▼
    Raspberry Pi ───────────────────────► FastAPI
           │                                  │
          YOLO                                ├── SQLite
           │                                  ├── Images
       Detection                              └── MQTT
                                                 │
                                                 ▼
                                               ESP32
                                                 │
                                               Relay
                                                 │
                                      Pump / Valve / Buzzer
```

**Core principle:** React talks to FastAPI. FastAPI owns the database, business logic, device communication, and MQTT integration. The camera, Raspberry Pi, YOLO, ESP32, and MQTT details remain behind the backend boundary.

**Document status:** API contract for current parallel frontend/backend development. Update this document whenever an agreed API contract changes.
