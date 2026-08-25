# PoolGuard Devices

The two hardware-side programs of the Swimming Pool Drowning Detection project:

```
devices/
├── esp32/poolguard_rescue/     Firmware: motorized rescue rod controller
└── raspberry_pi/               detector.py: camera + YOLO detection client
```

Neither device ever talks to the other directly. Both talk only to the FastAPI backend — the Pi over HTTP, the ESP32 over MQTT — exactly as the API contract requires.

---

## 1. ESP32 Rescue Firmware (`esp32/poolguard_rescue/poolguard_rescue.ino`)

Controls the motorized rod with a net that pushes a drowning person from the lowest point of the pool to the surface, then returns to its start position. **No pump, no buzzer, no strobe, no water-level sensor.**

### Wiring (ESP32 ↔ L298N)

```
ESP32 GPIO 26 ──► L298N IN1      (direction)
ESP32 GPIO 27 ──► L298N IN2      (direction)
ESP32 GPIO 25 ──► L298N ENA      (PWM speed)
ESP32 GND     ──► L298N GND      ← COMMON GROUND IS MANDATORY
Motor supply+ ──► L298N +12V     (separate motor battery/adapter)
L298N OUT1/2  ──► DC motor
```

Do **not** power the motor from the ESP32's 5V/3.3V pins — the motor's current spikes will reset or destroy the board. Separate supply, shared ground.

### Flash it

1. Arduino IDE → install the **ESP32 board package** (Boards Manager) and the **PubSubClient** library (Library Manager).
2. Edit the config block at the top of the `.ino`: WiFi SSID/password and `MQTT_HOST` (the laptop's LAN IP running Mosquitto — find it with `ipconfig`/`ifconfig`; not 127.0.0.1).
3. Select your ESP32 board + port, upload, open Serial Monitor at 115200 to watch it connect.

### How it behaves

- Publishes `{"device_id":"esp32-rescue-01","state":"..."}` on `poolguard/rescue/status` — on every state change **and** as a 5-second heartbeat (this is how the dashboard knows it's online).
- On `DEPLOY_RESCUE` (topic `poolguard/rescue/command`): runs the **non-blocking state machine** `IDLE → DEPLOYING → pause at surface → RETURNING → IDLE`. Non-blocking means `loop()` keeps servicing MQTT while the motor runs — never use `delay()` for the motion.
- Ignores deploy commands while already moving (second safety layer under the backend's 30 s cooldown).
- Motor is forced OFF at boot.

### Must tune on the real mechanism

`DEPLOY_TIME_MS`, `RETURN_TIME_MS`, `SURFACE_PAUSE_MS`, `MOTOR_SPEED`. Motion is currently **time-based**. Strongly recommended upgrade: two **limit switches** (end stops) so the motor stops on physical position rather than a timer — cheap, and removes drift/stall risk.

### Why this hardware (short version — full comparison in root README)

- **ESP32** over Arduino Uno (no WiFi) or a Pi (overkill; an OS on the safety actuator is a liability): built-in WiFi, PWM, $5, instant boot.
- **L298N** over a relay: a relay is on/off in one direction — the rod *must reverse* to return, and PWM gives controllable speed. Known weakness: ~2 V internal drop; if torque is low, raise the supply voltage and mind the heatsink. TB6612FNG is the efficient upgrade later.
- **MQTT** over HTTP polling: a rescue command must arrive *instantly*, not on the next poll.

---

## 2. Raspberry Pi Detection Client (`raspberry_pi/detector.py`)

Reads the IP camera's RTSP stream, runs YOLO person detection, and reports to the backend:

- `POST /video/frame` (~1 fps) → the dashboard's live view
- `POST /detection` (rate-limited per event type) → history, alerts, and — for DROWNING ≥ 0.85 — the automatic rescue

Runs unchanged on **Raspberry Pi 4 or 5** (pure Python; the Pi 5 just gives ~2–3× the YOLO fps).

### Run

```bash
pip install -r requirements.txt

# Real mode
python detector.py --rtsp rtsp://user:pass@CAMERA_IP:554/stream --api http://LAPTOP_IP:8000

# Mock mode — no camera, no YOLO, only `pip install requests pillow` needed
python detector.py --mock
```

**Mock mode** generates synthetic frames plus periodic detections, including a high-confidence DROWNING every ~30 s — it exercises the entire chain (backend → DB → MQTT → rod → dashboard) from any laptop. Use it for all integration testing.

### The one thing that MUST change before real use

`_classify_event()` is a **clearly marked placeholder**. It deliberately never returns `DROWNING`, because a DROWNING event physically moves the rescue rod. Real drowning classification needs one of:

1. a **temporal rule** — e.g., a person low in the frame with near-zero movement for N seconds, or
2. a **custom-trained YOLO model** fine-tuned on drowning footage.

Either plugs into the same function; the API contract does not change.

### Why this stack (short version)

- **YOLOv8-nano (Ultralytics)** over Haar cascades (poor with occlusion/splashing), MediaPipe (near-camera single subjects), SSD (weaker tooling): fast on a Pi CPU, excellent person detection out of the box, and fine-tunable on drowning data later.
- **OpenCV** for RTSP capture + JPEG encoding — the standard, effectively without competition.
- **requests** for HTTP — the standard Python client; nothing fancier is needed for two endpoints.

---

## 3. Full-System Bring-Up Order

1. Laptop only: broker + backend + `esp32_simulator.py` + dashboard + `detector.py --mock`. Everything should already work.
2. Replace the simulator with the real ESP32 (bench-test the motor **off the mechanism** first).
3. Replace mock with the real camera on the Pi (`--rtsp`), placeholder classifier still active (no DROWNING possible).
4. Only after 1–3 are stable: implement real drowning classification, test with the rod **detached from the net**, then assemble.

Safety first: never test classifier changes with the rod attached to the live mechanism.
