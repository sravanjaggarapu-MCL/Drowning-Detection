// ============================================================
// FILE: poolguard_rescue.ino
//
// PROJECT: Swimming Pool Drowning Detection (PoolGuard)
//
// PURPOSE:
// ESP32 firmware for the motorized rescue mechanism.
// A DC motor (driven through an L298N module) moves a rod
// with a net that pushes a drowning person from the lowest
// point of the pool up to the surface, then returns the rod
// to its original position.
//
// RESPONSIBILITIES:
// - Connect to WiFi and the MQTT broker.
// - Listen for rescue commands from the FastAPI backend.
// - Drive the DC motor through the L298N (deploy + return).
// - Publish the mechanism state so the backend/dashboard
//   always know what the device is doing.
//
// ARCHITECTURE:
//
// FastAPI backend
//      |
//      | MQTT publish: poolguard/rescue/command
//      v
//   ESP32 (this firmware)
//      |
//      | GPIO (IN1 / IN2 / ENA PWM)
//      v
//    L298N ──► DC motor ──► rod + net
//      |
//      | MQTT publish: poolguard/rescue/status
//      v
// FastAPI backend ──► React dashboard
//
// HARDWARE WIRING (L298N):
//
//   ESP32 GPIO 26  ──► L298N IN1
//   ESP32 GPIO 27  ──► L298N IN2
//   ESP32 GPIO 25  ──► L298N ENA   (PWM speed control)
//   ESP32 GND      ──► L298N GND   (COMMON ground, required!)
//   Motor supply + ──► L298N +12V  (motor battery/adapter)
//   L298N OUT1/2   ──► DC motor terminals
//
// NOTES:
// - There is NO pump, NO buzzer, NO strobe, and NO
//   water-level sensor in this project.
// - Motion is TIME-BASED: the motor runs for a fixed number
//   of milliseconds in each direction. Tune DEPLOY_TIME_MS /
//   RETURN_TIME_MS to the rod's real travel distance.
//   RECOMMENDED UPGRADE: add two limit switches (end stops)
//   so the motor stops on physical position, not time.
// - The L298N drops ~2V internally; power the motor with a
//   supply rated ABOVE the motor voltage if torque is low.
//
// LIBRARIES (Arduino IDE → Library Manager):
// - PubSubClient (by Nick O'Leary)  → MQTT
// - WiFi (built into the ESP32 board package)
// ============================================================


#include <WiFi.h>
#include <PubSubClient.h>


// ============================================================
// CONFIGURATION — EDIT THESE FOR YOUR NETWORK
// ============================================================

// WiFi credentials.
const char* WIFI_SSID     = "Motivity-CAccess";
const char* WIFI_PASSWORD = "M0t1v1ty#987CA";

// IP of the machine running the MQTT broker
// (the laptop running Mosquitto + FastAPI during development).
const char* MQTT_HOST = "172.16.3.39";
const int   MQTT_PORT = 1883;

// MQTT topics — MUST match app/services/mqtt_service.py.
const char* COMMAND_TOPIC = "poolguard/rescue/command";
const char* STATUS_TOPIC  = "poolguard/rescue/status";

// Identifier reported in every status message.
const char* DEVICE_ID = "esp32-rescue-01";


// ============================================================
// L298N PIN CONFIGURATION
// ============================================================

// Direction pins: IN1/IN2 select motor direction.
const int PIN_IN1 = 26;
const int PIN_IN2 = 27;

// Enable pin: PWM duty cycle controls motor speed.
const int PIN_ENA = 25;

// PWM setup for the ENA pin.
const int PWM_FREQ_HZ    = 1000;  // 1 kHz is fine for L298N.
const int PWM_RESOLUTION = 8;     // Duty range 0–255.
const int MOTOR_SPEED    = 220;   // ~86% power. Tune for torque.


// ============================================================
// MOTION TIMING — TUNE ON THE REAL MECHANISM
// ============================================================

// How long the motor runs to push the rod from the pool's
// lowest point up to the surface.
const unsigned long DEPLOY_TIME_MS = 4000;

// How long the motor runs (reversed) to bring the rod back
// to its original position. Usually equal to DEPLOY_TIME_MS.
const unsigned long RETURN_TIME_MS = 4000;

// Short pause at the surface so the person can grab the net
// or be pushed clear before the rod retracts.
const unsigned long SURFACE_PAUSE_MS = 2000;

// Heartbeat interval — same rhythm the backend expects.
const unsigned long HEARTBEAT_MS = 5000;


// ============================================================
// STATE MACHINE
// ============================================================
// The rescue motion is non-blocking: loop() keeps running so
// MQTT stays connected while the motor moves. States match
// what the backend/mqtt_service.py understands.
// ============================================================

enum RescueState {
  STATE_IDLE,       // Rod at rest position, ready.
  STATE_DEPLOYING,  // Motor pushing rod toward surface.
  STATE_PAUSING,    // Rod holding at surface.
  STATE_RETURNING   // Motor bringing rod back.
};

RescueState currentState = STATE_IDLE;

// When the current motion phase started (millis()).
unsigned long phaseStartTime = 0;

// When the last heartbeat was published.
unsigned long lastHeartbeatTime = 0;


// ============================================================
// NETWORK CLIENTS
// ============================================================

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);


// ============================================================
// MOTOR CONTROL HELPERS
// ============================================================

// Drive the motor in the DEPLOY direction (rod goes up).
void motorDeploy() {
  digitalWrite(PIN_IN1, HIGH);
  digitalWrite(PIN_IN2, LOW);
  ledcWrite(PIN_ENA, MOTOR_SPEED);
}

// Drive the motor in the RETURN direction (rod goes back).
void motorReturn() {
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, HIGH);
  ledcWrite(PIN_ENA, MOTOR_SPEED);
}

// Stop the motor completely.
void motorStop() {
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, LOW);
  ledcWrite(PIN_ENA, 0);
}


// ============================================================
// STATUS PUBLISHING
// ============================================================

// Convert the state enum into the contract string.
const char* stateName() {
  switch (currentState) {
    case STATE_DEPLOYING: return "DEPLOYING";
    case STATE_PAUSING:   return "DEPLOYING";  // Still "out".
    case STATE_RETURNING: return "RETURNING";
    default:              return "IDLE";
  }
}

// Publish the current state as JSON, e.g.:
// {"device_id":"esp32-rescue-01","state":"IDLE"}
void publishStatus() {
  char payload[96];

  snprintf(
    payload,
    sizeof(payload),
    "{\"device_id\":\"%s\",\"state\":\"%s\"}",
    DEVICE_ID,
    stateName()
  );

  mqttClient.publish(STATUS_TOPIC, payload);
}


// ============================================================
// RESCUE SEQUENCE CONTROL
// ============================================================

// Begin the rescue motion (called when a command arrives).
void startRescue() {

  // Ignore commands while the rod is already moving. The
  // backend cooldown normally prevents this, but the device
  // protects itself as well.
  if (currentState != STATE_IDLE) {
    Serial.println("[rescue] Busy - command ignored");
    return;
  }

  Serial.println("[rescue] DEPLOYING net rod!");

  currentState = STATE_DEPLOYING;
  phaseStartTime = millis();

  motorDeploy();
  publishStatus();
}

// Advance the non-blocking state machine. Called every loop().
void updateRescue() {

  unsigned long elapsed = millis() - phaseStartTime;

  switch (currentState) {

    case STATE_DEPLOYING:
      // Rod has reached the surface: stop and hold.
      if (elapsed >= DEPLOY_TIME_MS) {
        motorStop();
        currentState = STATE_PAUSING;
        phaseStartTime = millis();
        Serial.println("[rescue] At surface - pausing");
      }
      break;

    case STATE_PAUSING:
      // Pause finished: bring the rod back.
      if (elapsed >= SURFACE_PAUSE_MS) {
        currentState = STATE_RETURNING;
        phaseStartTime = millis();
        motorReturn();
        publishStatus();
        Serial.println("[rescue] RETURNING to start position");
      }
      break;

    case STATE_RETURNING:
      // Rod is back at its original position: done.
      if (elapsed >= RETURN_TIME_MS) {
        motorStop();
        currentState = STATE_IDLE;
        publishStatus();
        Serial.println("[rescue] Complete - IDLE");
      }
      break;

    default:
      // IDLE: nothing to do.
      break;
  }
}


// ============================================================
// MQTT CALLBACK
// ============================================================

// Called for every message on a subscribed topic.
//
// Expected command payload from the backend:
// {"action":"DEPLOY_RESCUE","reason":"...","request_id":"..."}
void onMqttMessage(char* topic, byte* payload, unsigned int length) {

  Serial.print("[mqtt] Message on ");
  Serial.println(topic);

  // Copy the payload into a null-terminated buffer.
  char message[256];
  unsigned int copyLen = min(length, (unsigned int)(sizeof(message) - 1));
  memcpy(message, payload, copyLen);
  message[copyLen] = '\0';

  // Simple substring check keeps the firmware free of a JSON
  // library dependency; the action string is unique enough.
  if (strstr(message, "DEPLOY_RESCUE") != NULL) {
    startRescue();
  }
}


// ============================================================
// CONNECTION HELPERS
// ============================================================

void connectWiFi() {
  Serial.print("[wifi] Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Block until WiFi is up; the device is useless without it.
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.print("\n[wifi] Connected. IP: ");
  Serial.println(WiFi.localIP());
}

void connectMqtt() {

  while (!mqttClient.connected()) {

    Serial.println("[mqtt] Connecting to broker...");

    if (mqttClient.connect(DEVICE_ID)) {

      Serial.println("[mqtt] Connected");

      // Listen for rescue commands from the backend.
      mqttClient.subscribe(COMMAND_TOPIC);

      // Announce our state immediately.
      publishStatus();

    } else {
      Serial.print("[mqtt] Failed rc=");
      Serial.println(mqttClient.state());
      delay(2000);
    }
  }
}


// ============================================================
// ARDUINO SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  // Configure the L298N control pins.
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);

  // Attach PWM to the enable pin (ESP32 Arduino core 3.x API).
  ledcAttach(PIN_ENA, PWM_FREQ_HZ, PWM_RESOLUTION);

  // SAFETY: make sure the motor is stopped at boot.
  motorStop();

  // Bring up the network.
  connectWiFi();

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
}


// ============================================================
// ARDUINO MAIN LOOP
// ============================================================

void loop() {

  // Keep the MQTT connection alive (auto-reconnect).
  if (!mqttClient.connected()) {
    connectMqtt();
  }

  // Process incoming/outgoing MQTT traffic.
  mqttClient.loop();

  // Advance the rescue motion state machine.
  updateRescue();

  // Publish the heartbeat so the backend knows we're online.
  if (millis() - lastHeartbeatTime >= HEARTBEAT_MS) {
    lastHeartbeatTime = millis();
    publishStatus();
  }
}
