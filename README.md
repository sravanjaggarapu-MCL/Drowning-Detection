# PoolGuard — Swimming Pool Drowning Detection

PoolGuard is a swimming-pool safety system. An IP camera watches the pool, a Raspberry Pi runs YOLO computer vision to detect people and possible drowning, a FastAPI backend records every event and shows it on a React dashboard, and when a high-confidence drowning is detected, an ESP32 drives a motorized rod with a net (through an L298N motor driver) that pushes the person from the lowest point of the pool up to the surface, then returns to its original position.

There is **no drain pump, no buzzer, no strobe, and no water-level sensor** in this project. The rescue hardware is only the motorized net rod.

---

## 1. Big Picture Architecture

```
IP Camera
    │  RTSP video stream
    ▼
Raspberry Pi 4 or 5  ──── runs YOLO person detection
    │
    │  HTTP (POST /detection, POST /video/frame)
    ▼
FastAPI Backend  ◄────────────── HTTP ──────────────  React Dashboard
    │  owns: SQLite DB, detection images,                 (browser)
    │        business logic, MQTT
    │
    │  MQTT (poolguard/rescue/command)
    ▼
ESP32
    │  GPIO
    ▼
L298N Motor Driver
    │
    ▼
DC Motor ──► Rod + Net (deploy to surface, then return)
```

**The one rule that explains everything:** React talks *only* to FastAPI. FastAPI owns the database, the images, the business logic, and all device communication. The camera, YOLO, Raspberry Pi, MQTT, and ESP32 are invisible to the frontend. This is defined in the API contract and it is why each part of the system can be built and tested independently.

---

## 2. Repository Layout

```
PoolGuard/
├── SwimBackend/                  FastAPI backend (laptop/server)
│   ├── app/
│   │   ├── main.py               App entry: CORS, routers, MQTT lifespan
│   │   ├── models/               SQLAlchemy: database.py, detection.py
│   │   ├── schemas/              Pydantic: detection.py, device.py
│   │   ├── services/             Business logic: detection, video, mqtt
│   │   └── routes/               HTTP endpoints: detection, video, device
│   ├── data/                     SQLite DB + stored images/frames
│   ├── tools/esp32_simulator.py  Fake ESP32 for hardware-free testing
│   └── requirements.txt
│
├── SwimFrontend/pool-drowning-dashboard/    React dashboard (Vite)
│   └── src/
│       ├── api/                  client.js, detectionApi, videoApi, deviceApi
│       ├── utils/                detectionDisplay.js (API value → UI value)
│       ├── components/           CameraView, AlertPanel, RescuePanel, ...
│       └── pages/                Landing, Login, Dashboard, Events
│
├── devices/
│   ├── esp32/poolguard_rescue/   Arduino firmware for the rescue rod
│   └── raspberry_pi/             detector.py (RTSP + YOLO client)
│
├── PoolGuard_Frontend_Backend_API_Contract.pdf    Main contract
└── PoolGuard_Device_API_Contract_Addendum.md      Device endpoints + MQTT
```

---

## 3. Recommended Learning Order

Follow this order. Each step builds on the previous one, and each points at the exact files to read. Every code file in this project has a header explaining its purpose, responsibilities, and architecture — read the headers first, then the code.

### Step 1 — The API contract (the map of everything)
Read `PoolGuard_Frontend_Backend_API_Contract.pdf` and then the device addendum. Don't study any code yet. Understand: which endpoints exist, what fields they use (snake_case), and the rule that React only talks to FastAPI. Every other file in the project is just an implementation of this document.

### Step 2 — HTTP and JSON fundamentals
Make sure you can answer: what is GET vs POST, what do status codes 200/404/422/500 mean, what is JSON, and what is `multipart/form-data` (used because detections can carry an image). Test the ideas against the live backend using the automatic Swagger UI at `http://127.0.0.1:8000/docs` — this alone teaches most of HTTP.

### Step 3 — The backend, from the bottom up
Read the files in this order; it mirrors how a request flows through layers:

1. `app/models/database.py` — how the SQLite connection and sessions work.
2. `app/models/detection.py` — what a detection row looks like in the database.
3. `app/schemas/detection.py` — how Pydantic validates API data (and why the DB model and API schema are separate things).
4. `app/services/detection_service.py` — the business logic: saving images to disk, storing rows, and the auto-rescue rule.
5. `app/routes/detection.py` — how HTTP requests become service calls.
6. `app/routes/video.py` + `app/services/video_service.py` — the simpler video pair; good reinforcement of the same pattern.
7. `app/main.py` — how it all gets assembled, plus CORS and the MQTT lifespan.

The pattern to internalize: **routes → services → models**, each layer with one job. This is the most transferable thing in the whole project.

### Step 4 — The frontend, from the API layer up
1. `.env` and `src/api/client.js` — one base URL, one shared request function.
2. `src/api/videoApi.js`, `detectionApi.js`, `deviceApi.js` — one module per backend area.
3. `src/utils/detectionDisplay.js` — how raw API values (DROWNING, 0.93) become UI values (🚨 "Drowning Detected", "93%") without ever changing the API values.
4. Components in this order: `StatusCard` (props), `RecentEvents` (fetching + loading/empty/error states), `AlertPanel` and `CameraView` (polling with `setInterval` + cleanup), `RescuePanel` (POSTing an action).
5. `pages/Dashboard.jsx` and `App.jsx` — composition and navigation.

React concepts you need along the way: components/props, `useState`, `useEffect`, and why effects return a cleanup function.

### Step 5 — MQTT and the ESP32
1. Read `app/services/mqtt_service.py` — topics, heartbeat, cooldown, why MQTT is used at all.
2. Read `tools/esp32_simulator.py` — the same protocol in ~150 simple lines.
3. Run the hardware-free demo (section 5 below) and watch messages flow.
4. Only then read the firmware `devices/esp32/poolguard_rescue/poolguard_rescue.ino` — the state machine (IDLE → DEPLOYING → PAUSING → RETURNING) and the L298N pin control.

### Step 6 — Computer vision (the Raspberry Pi side)
Read `devices/raspberry_pi/detector.py`. Concepts: what RTSP is, how OpenCV reads frames, what YOLO does (finds people + gives a confidence), and why the drowning classifier is a placeholder that must be replaced with a temporal rule or trained model before it's real. Run it in `--mock` mode first; touch the real camera last.

### Step 7 — Integration
Run the full no-hardware demo, trigger events, watch them travel: mock detector → backend → database → dashboard, and DROWNING ≥ 0.85 → MQTT → simulated rod motion → RescuePanel. When that chain makes sense, you understand the entire project.

---

## 4. Tech Stack: What We Use, and Why (vs. the Alternatives)

### Backend framework — **FastAPI** (Python)

| Option | Verdict for this project |
|---|---|
| **FastAPI ✅** | Async Python, automatic request validation via Pydantic, and free interactive docs at `/docs`. Same language as the YOLO/OpenCV world, so the whole detection side of the team stays in Python. |
| Flask | Simpler and older, but validation, docs, and typed request models must be added by hand — FastAPI gives exactly those for free, and this project leans on 422 validation heavily. |
| Django (+DRF) | Batteries included (admin, auth, ORM), but far heavier than needed for ~10 JSON endpoints. Its structure would dominate a small project. |
| Node.js/Express | Fine framework, but it splits the team across two languages: the CV code (YOLO/OpenCV) is Python no matter what. One backend language beats two. |

**Deciding factor:** automatic validation + Swagger docs + Python ecosystem shared with the computer-vision code.

### Database — **SQLite** (via SQLAlchemy)

| Option | Verdict |
|---|---|
| **SQLite ✅** | Zero installation, zero server, the whole DB is one file (`data/poolguard.db`). Perfect for a single-writer system (only FastAPI touches it) with modest event volume. |
| PostgreSQL / MySQL | The right choice *later* for multi-user production. Right now they add a server to install, configure, and secure — pure overhead during development. |
| MongoDB | Detection events are rigidly structured rows (id, device_id, type, confidence, timestamp). That is exactly a relational table; a document store buys nothing here. |

**Deciding factor:** simplicity. And because we access it through **SQLAlchemy** (not raw SQL), migrating to PostgreSQL later means changing one connection string, not the codebase. Note also: images are stored on the filesystem and only the *filename* goes in the DB — databases are bad at blobs, filesystems are great at files.

### Frontend — **React + Vite**

| Option | Verdict |
|---|---|
| **React ✅** | Component model fits a dashboard perfectly (StatusCard, CameraView, RescuePanel are natural components), `useState`/`useEffect` handle the constant polling cleanly, and it has the largest ecosystem/learning resources. |
| Vue / Svelte | Genuinely good, arguably easier to start. React was chosen for team familiarity and ecosystem size — for a team project, the stack people can get help with wins. |
| Angular | A full enterprise framework (DI, modules, RxJS). Massive overkill for a four-page dashboard. |
| Plain HTML/JS | Would work for one page, but live-updating panels sharing state (alert + events + device status) becomes spaghetti fast without a component model. |

**Build tool — Vite** over Create React App: CRA is deprecated; Vite starts in milliseconds, has trivial env handling (`VITE_API_URL`), and is the current standard.

### Backend ↔ ESP32 — **MQTT (Mosquitto broker)**

This is the most instructive choice in the project.

| Option | Verdict |
|---|---|
| **MQTT ✅** | Built for tiny devices: a persistent, lightweight pub/sub connection. The backend *pushes* `DEPLOY_RESCUE` and the ESP32 reacts instantly. Heartbeats over the same channel give online/offline detection for free. This is the industry-standard IoT protocol. |
| ESP32 polls HTTP | The ESP32 would have to ask "any command for me?" every second — a rescue command could wait a full polling interval **in a drowning emergency**, and the backend gets hammered with useless requests. Latency you can't accept. |
| ESP32 runs an HTTP server | Then the backend must know the ESP32's IP (which changes with DHCP), and firmware HTTP servers are fragile. MQTT inverts this: the device connects *out* to a known broker. |
| WebSockets | Push works, but there's no broker, no topics, no QoS, and ESP32 WebSocket libraries are weaker than PubSubClient. You'd rebuild half of MQTT by hand. |

**Deciding factor:** near-instant push for an emergency command + trivial device presence detection. Broker is **Mosquitto** (local, one command to run) rather than a cloud broker (AWS IoT, HiveMQ) — no internet dependency for a life-safety local system.

### Rescue controller — **ESP32**

| Option | Verdict |
|---|---|
| **ESP32 ✅** | Built-in WiFi (MQTT needs a network!), dual-core, plenty of PWM pins, ~$5. The de-facto standard for WiFi IoT control. |
| Arduino Uno/Nano | No WiFi. You'd bolt on an ESP8266/shield anyway — at which point just use the ESP32. |
| Raspberry Pi as motor controller | Wildly overqualified, boots an entire OS (slow, SD-card corruption risk on power loss), and costs 10× more. Also bad engineering to put vision *and* actuation on one device: the Pi is busy running YOLO; the safety actuator should be a dumb, reliable, instant-on microcontroller. |

### Motor driver — **L298N**

| Option | Verdict |
|---|---|
| **L298N ✅** | Dirt cheap, everywhere, handles the DC motor's current, gives direction control (IN1/IN2) + speed (PWM on ENA) — exactly the deploy/reverse/speed control the rod needs. Enormous amount of tutorials/wiring diagrams, which matters for a student/hardware-learning project. |
| Single relay | On/off only, **one direction** — but the rod must reverse to return to its start position. A relay fundamentally can't do this job. Dual-relay H-bridges exist but give no speed control. |
| TB6612FNG | Technically better (more efficient, less voltage drop). Fine upgrade later; smaller community and the L298N you already own works. |
| BTS7960 | For big high-current motors. Only needed if the final rod motor draws more than the L298N's ~2 A continuous. |

**Honest limitation to know:** the L298N wastes ~2 V internally as heat. If the rod feels weak, supply a voltage *above* the motor's rating (e.g., 12 V supply for a 9–10 V effective drive) and check the heatsink.

### Computer vision — **YOLO (Ultralytics, yolov8n) + OpenCV**

| Option | Verdict |
|---|---|
| **YOLOv8-nano ✅** | Single-pass detector: fast enough for a Pi CPU at ~1–2 fps, excellent person detection out of the box (`classes=[0]`), 3-line Python API, and the same framework can later be *fine-tuned on drowning data* — the natural growth path. |
| Haar cascades (classic OpenCV) | 2001-era technology; poor with partial occlusion, splashing water, unusual poses — i.e., poor at exactly what a pool looks like. |
| MediaPipe Pose | Great skeletons, but tuned for near-camera single subjects; struggles with distant/partially submerged people. Could *complement* YOLO later for motion analysis. |
| SSD-MobileNet | Comparable speed class, but a worse tooling/training story than Ultralytics in 2026. |

**OpenCV** handles the RTSP capture and JPEG encoding — it is the only serious option there, no real alternative to compare.

### Vision computer — **Raspberry Pi 4 or 5**

Either works: the client is pure Python. Pi 5 gives roughly 2–3× the CPU inference speed (more YOLO fps → faster detection), Pi 4 is cheaper and sufficient for ~1 fps nano-model inference. The code takes no side, so the hardware decision can wait. (A Jetson Nano would add GPU inference but costs more and adds CUDA complexity — unnecessary at this stage.)

### The meta-pattern

Every choice follows the same logic: **the simplest tool that genuinely does the job now, chosen so upgrading later doesn't require rewrites.** SQLite → PostgreSQL is one config line (thanks to SQLAlchemy). L298N → TB6612 is rewiring, not recoding. yolov8n → a fine-tuned drowning model is a file swap. That is deliberate architecture, and it's worth being able to say out loud when presenting the project.

---

## 5. Quick Start (no hardware needed)

Prerequisites: Python 3.11+, Node.js 18+, Mosquitto ([mosquitto.org/download](https://mosquitto.org/download)).

```bash
# Terminal 1 — MQTT broker
mosquitto -p 1883

# Terminal 2 — Backend
cd SwimBackend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger docs: http://127.0.0.1:8000/docs

# Terminal 3 — Fake ESP32 (behaves exactly like the firmware)
cd SwimBackend
python tools/esp32_simulator.py

# Terminal 4 — Dashboard
cd SwimFrontend/pool-drowning-dashboard
npm install
npm run dev
# Open http://localhost:5173

# Terminal 5 (optional) — Fake camera + detections
cd devices/raspberry_pi
pip install requests pillow
python detector.py --mock
```

What you'll see: a live (mock) camera feed, events filling the dashboard, and every ~30 s a high-confidence DROWNING that automatically "deploys" the simulated rescue rod — watch the Rescue System panel go Ready → Deploying → Returning → Ready.

Manual rescue test: click **🚨 Deploy Rescue** on the dashboard, or:

```bash
curl -X POST http://127.0.0.1:8000/device/emergency
```

With real hardware, replace Terminal 3 with the flashed ESP32 (edit WiFi/broker IP in the `.ino` first) and Terminal 5 with `python detector.py --rtsp rtsp://user:pass@CAMERA_IP:554/stream` on the Pi.

---

## 6. Where Each Rule Lives (cheat sheet)

| Rule | Where it's enforced |
|---|---|
| API fields are snake_case, values like `DROWNING` never change | Contract §4/§8; schemas + `detectionDisplay.js` translate for UI only |
| Confidence stored as 0.0–1.0, shown as % | Contract §12; `formatConfidence()` in the frontend |
| React never sees MQTT/RTSP/YOLO/SQLite | Contract §3/§16/§17; only `src/api/*` talks to the network |
| DROWNING ≥ 0.85 auto-deploys the rod | `detection_service.py` (`AUTO_RESCUE_CONFIDENCE_THRESHOLD`) |
| Rod can't be re-triggered mid-motion | 30 s cooldown in `mqtt_service.py` + busy-check in firmware |
| Device considered offline after 15 s silence | `mqtt_service.py` (`DEVICE_TIMEOUT_SECONDS`) |
| Images live on disk, DB stores only filenames | Contract §11; `detection_service.save_detection_image()` |

---

## 7. Documents

- `PoolGuard_Frontend_Backend_API_Contract.pdf` — the main contract (read first).
- `PoolGuard_Device_API_Contract_Addendum.md` — device endpoints, MQTT topics, auto-rescue rule. Must be agreed by both developers per contract §5.
- Component READMEs: `SwimBackend/README.md`, `SwimFrontend/pool-drowning-dashboard/README.md`, `devices/README.md`.
