// ============================================================
// FILE: RescuePanel.jsx
//
// PURPOSE:
// This component displays the rescue mechanism (motorized
// net rod) status and provides a manual emergency trigger.
//
// RESPONSIBILITIES:
// - Load the rescue device status from the backend.
// - Refresh the status automatically.
// - Show whether the ESP32 is online and what the rod is
//   currently doing (IDLE / DEPLOYING / RETURNING).
// - Provide a confirmed manual "Deploy Rescue" button.
//
// DATA SOURCE:
//
// RescuePanel
//      |
//      v
// deviceApi.js ──► GET  /device/status
//                  POST /device/emergency
//      |
//      v
// FastAPI ──MQTT──► ESP32 ──► L298N ──► DC motor ──► net rod
//
// IMPORTANT:
// - This component does NOT talk to MQTT or the ESP32.
//   All hardware communication stays behind FastAPI
//   (contract sections 16/17).
// - The manual trigger asks for confirmation because it
//   physically moves the rescue mechanism.
// ============================================================


import { useEffect, useState } from "react";

import {
  getDeviceStatus,
  triggerEmergencyRescue,
} from "../api/deviceApi";


// How often the device status is refreshed (ms).
//
// 3 seconds keeps the panel current while the rod moves
// (a full deploy+return cycle takes several seconds).
const REFRESH_INTERVAL_MS = 3000;


// Friendly display text for each device state.
const STATE_LABELS = {
  IDLE: "Ready",
  DEPLOYING: "Deploying net rod...",
  RETURNING: "Returning to position...",
  ERROR: "Device error",
  UNKNOWN: "Unknown",
};


// Create the RescuePanel component.
function RescuePanel() {

  // Latest device status from the backend, or null while
  // the first request is still running.
  const [device, setDevice] = useState(null);

  // True while a manual rescue request is in flight.
  const [triggering, setTriggering] = useState(false);

  // Result/error message from the last manual trigger.
  const [actionMessage, setActionMessage] = useState(null);


  // ----------------------------------------------------------
  // LOAD DEVICE STATUS (WITH AUTO-REFRESH)
  // ----------------------------------------------------------

  useEffect(() => {

    async function loadStatus() {

      try {

        // GET /device/status
        const status = await getDeviceStatus();

        setDevice(status);

      } catch (err) {

        // Backend unreachable: represent as fully offline.
        console.error("Unable to load device status:", err);

        setDevice({
          device_id: null,
          online: false,
          state: "UNKNOWN",
          last_seen: null,
          message: "Backend unreachable",
        });
      }
    }

    // Run immediately on mount.
    loadStatus();

    // Then repeat on a fixed interval.
    const intervalId = setInterval(
      loadStatus,
      REFRESH_INTERVAL_MS
    );

    // Stop refreshing when the component is removed.
    return () => clearInterval(intervalId);

  }, []);


  // ----------------------------------------------------------
  // MANUAL EMERGENCY TRIGGER
  // ----------------------------------------------------------

  async function handleEmergency() {

    // The button physically moves hardware, so require an
    // explicit confirmation from the operator.
    const confirmed = window.confirm(
      "Deploy the rescue mechanism now?\n\n" +
      "The net rod will push up to the surface and then " +
      "return to its start position."
    );

    if (!confirmed) {
      return;
    }

    setTriggering(true);
    setActionMessage(null);

    try {

      // POST /device/emergency
      const result = await triggerEmergencyRescue();

      // Show the backend's confirmation text.
      setActionMessage(result.message);

    } catch (err) {

      // 429 (cooldown) and 503 (device unavailable) arrive
      // here with the backend's detail message.
      setActionMessage(err.message);

    } finally {
      setTriggering(false);
    }
  }


  // ----------------------------------------------------------
  // DERIVE DISPLAY VALUES
  // ----------------------------------------------------------

  // True only when the ESP32 heartbeat is recent.
  const online = device ? device.online : false;

  // Raw state string from the backend.
  const state = device ? device.state : "UNKNOWN";

  // Friendly state label (falls back to the raw value).
  const stateLabel = STATE_LABELS[state] || state;

  // The rod is physically moving in these states.
  const busy = state === "DEPLOYING" || state === "RETURNING";


  // ----------------------------------------------------------
  // RENDER
  // ----------------------------------------------------------

  return (

    // Rescue panel container (reuses alert-panel styling).
    <div className="alert-panel rescue-panel">

      {/* Panel heading. */}
      <div className="panel-heading">

        {/* Net/rescue icon. */}
        <span>🛟</span>

        {/* Heading text. */}
        <h2>Rescue System</h2>

      </div>

      {/* Device state summary box. Turns amber while the
          rod is moving, red when the device is offline. */}
      <div
        className={
          `safe-message ${!online ? "danger" : busy ? "busy" : ""}`
        }
      >

        {/* Status icon. */}
        <div
          className={
            `safe-icon ${!online ? "danger" : busy ? "busy" : ""}`
          }
        >
          {!online ? "✕" : busy ? "…" : "✓"}
        </div>

        {/* Status information. */}
        <div>
          <h3>
            {online ? stateLabel : "Device Offline"}
          </h3>
          <p>
            {device ? device.message : "Checking device..."}
          </p>
        </div>

      </div>

      {/* Device information rows. */}
      <div className="alert-info">

        {/* ESP32 connection status. */}
        <div>
          <span>ESP32</span>
          <strong>{online ? "Online" : "Offline"}</strong>
        </div>

        {/* Mechanism state. */}
        <div>
          <span>Mechanism</span>
          <strong>{stateLabel}</strong>
        </div>

        {/* Device identifier. */}
        <div>
          <span>Device</span>
          <strong>{device?.device_id || "—"}</strong>
        </div>

      </div>

      {/* Manual emergency trigger. Disabled while the device
          is offline, already moving, or a request is
          in flight. */}
      <button
        className="rescue-button"
        onClick={handleEmergency}
        disabled={!online || busy || triggering}
      >
        {triggering
          ? "Sending command..."
          : "🚨 Deploy Rescue"}
      </button>

      {/* Result of the last manual trigger. */}
      {actionMessage && (
        <p className="rescue-message">
          {actionMessage}
        </p>
      )}

    </div>
  );
}

// Export the RescuePanel component.
export default RescuePanel;
