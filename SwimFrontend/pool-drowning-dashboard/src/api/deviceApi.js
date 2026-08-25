// ============================================================
// FILE: deviceApi.js
//
// PURPOSE:
// Provides frontend functions for communicating with the
// FastAPI rescue-device endpoints.
//
// RESPONSIBILITIES:
// - Get the current rescue device status.
// - Trigger an emergency rescue deployment.
//
// API ENDPOINTS USED:
//
// GET  /device/status
// POST /device/emergency
//
// ARCHITECTURE:
//
// React Component
//       |
//       v
// deviceApi.js
//       |
//       v
// client.js
//       |
//       | HTTP
//       v
// FastAPI ──MQTT──► ESP32 ──► L298N ──► rescue rod
//
// IMPORTANT:
// - React NEVER talks to MQTT or the ESP32 directly
//   (contract sections 16/17). Broker addresses, topics,
//   and credentials stay in the backend.
// - This file does NOT contain UI code.
// - API field names stay snake_case per the contract.
// ============================================================


// ============================================================
// IMPORT COMMON API CLIENT
// ============================================================
//
// apiRequest() handles:
// - Backend URL
// - HTTP requests
// - HTTP error handling (throws with FastAPI's detail text)
// ============================================================

import { apiRequest } from "./client";


// ============================================================
// GET DEVICE STATUS
// ============================================================
//
// Backend endpoint:
//
// GET /device/status
//
// Example response:
//
// {
//     "device_id": "esp32-rescue-01",
//     "online": true,
//     "state": "IDLE",
//     "last_seen": "2026-08-22T15:00:00",
//     "message": "Rescue device is online"
// }
//
// States: IDLE, DEPLOYING, RETURNING, ERROR, UNKNOWN.
//
// The frontend must use this response instead of assuming
// the device is connected (same rule as the video status).
// ============================================================

export async function getDeviceStatus() {

    // Send the request to FastAPI.
    const response = await apiRequest(
        "/device/status"
    );

    // Convert the JSON response into a JavaScript object.
    return response.json();
}


// ============================================================
// TRIGGER EMERGENCY RESCUE
// ============================================================
//
// Backend endpoint:
//
// POST /device/emergency
//
// The backend publishes an MQTT command; the ESP32 then
// drives the net rod up to the surface and back.
//
// Possible errors (thrown by client.js with the backend's
// detail message):
//
// - 429: a rescue was triggered very recently (cooldown).
// - 503: MQTT broker / device communication unavailable.
// ============================================================

export async function triggerEmergencyRescue() {

    // Send the request to FastAPI.
    const response = await apiRequest(
        "/device/emergency",
        {
            method: "POST",

            // The body is JSON, so the header is required
            // here (unlike FormData requests).
            headers: {
                "Content-Type": "application/json"
            },

            // "manual" marks dashboard-triggered rescues,
            // distinguishing them from "auto:..." triggers
            // created by the detection pipeline.
            body: JSON.stringify({
                reason: "manual"
            })
        }
    );

    // Return FastAPI's confirmation.
    return response.json();
}
