// ============================================================
// FILE: AlertPanel.jsx
//
// PURPOSE:
// This component displays the current safety condition of the
// swimming pool based on the newest detection event.
//
// RESPONSIBILITIES:
// - Load the latest detection from the FastAPI backend.
// - Show a DANGER state when the latest event is DROWNING.
// - Show a SAFE state for normal activity or no detections.
// - Refresh automatically so the panel stays current.
//
// DATA SOURCE:
//
// AlertPanel
//      |
//      v
// detectionApi.js ──► GET /detection/latest ──► FastAPI
//
// IMPORTANT:
// - This component does NOT call fetch() directly.
//   All backend communication goes through detectionApi.js.
// - A 404 from /detection/latest means "no detections yet"
//   and is treated as a normal safe/empty state
//   (detectionApi.getLatestDetection returns null for it).
// - The danger decision comes from the API event_type value,
//   translated in utils/detectionDisplay.js.
// ============================================================


import { useEffect, useState } from "react";

import { getLatestDetection } from "../api/detectionApi";

import {
  formatConfidence,
  formatEventTime,
  getEventDisplay,
} from "../utils/detectionDisplay";


// How often the panel re-checks the latest detection (ms).
//
// 5 seconds keeps the safety status current without
// overloading the backend.
const REFRESH_INTERVAL_MS = 5000;


// Create the AlertPanel component.
function AlertPanel() {

  // The newest detection, or null when none exists yet.
  const [latest, setLatest] = useState(null);

  // True when the backend could not be reached.
  const [backendError, setBackendError] = useState(false);


  // ----------------------------------------------------------
  // LOAD LATEST DETECTION (WITH AUTO-REFRESH)
  // ----------------------------------------------------------
  // Runs when the component mounts, then repeats on an
  // interval so a new DROWNING event appears without a
  // manual page reload.
  // ----------------------------------------------------------

  useEffect(() => {

    async function loadLatest() {

      try {

        // Ask the backend for the newest detection.
        //
        // Returns null when no detection exists yet (404).
        const detection = await getLatestDetection();

        // Store the result (may be null).
        setLatest(detection);

        // The backend responded, so clear any error.
        setBackendError(false);

      } catch (err) {

        // The backend itself is unreachable or failing.
        console.error("Unable to load latest detection:", err);
        setBackendError(true);
      }
    }

    // Run immediately on mount.
    loadLatest();

    // Then repeat on a fixed interval.
    const intervalId = setInterval(
      loadLatest,
      REFRESH_INTERVAL_MS
    );

    // Stop refreshing when the component is removed.
    return () => clearInterval(intervalId);

  }, []);


  // ----------------------------------------------------------
  // DERIVE DISPLAY STATE
  // ----------------------------------------------------------

  // Translate the latest event type into display info.
  //
  // When no detection exists, the pool is considered safe.
  const display = latest
    ? getEventDisplay(latest.event_type)
    : null;

  // The pool is in danger when the newest event is dangerous.
  const isDanger = display ? display.danger : false;


  // ----------------------------------------------------------
  // RENDER
  // ----------------------------------------------------------

  return (

    // Alert panel container.
    <div className="alert-panel">

      {/* Alert panel heading. */}
      <div className="panel-heading">

        {/* Bell icon. */}
        <span>🔔</span>

        {/* Heading text. */}
        <h2>Safety Status</h2>

      </div>

      {/* Current safety status. The "danger" class switches
          the panel from green to red styling. */}
      <div className={`safe-message ${isDanger ? "danger" : ""}`}>

        {/* Large status icon: check when safe, alert when
            a drowning event is active. */}
        <div className={`safe-icon ${isDanger ? "danger" : ""}`}>
          {isDanger ? "!" : "✓"}
        </div>

        {/* Safety information. */}
        <div>

          {isDanger ? (
            <>
              <h3>Drowning Alert</h3>
              <p>
                Possible drowning detected
                {latest && ` (${formatConfidence(latest.confidence)} confidence)`}.
              </p>
            </>
          ) : (
            <>
              <h3>Pool is Safe</h3>
              <p>No drowning activity detected.</p>
            </>
          )}

        </div>

      </div>

      {/* Monitoring information. */}
      <div className="alert-info">

        {/* Backend/AI monitoring status. */}
        <div>
          <span>AI Monitoring</span>
          <strong>
            {backendError ? "Offline" : "Active"}
          </strong>
        </div>

        {/* Time of the newest detection. */}
        <div>
          <span>Last Event</span>
          <strong>
            {latest
              ? formatEventTime(latest.timestamp)
              : "No events yet"}
          </strong>
        </div>

        {/* Newest event type (friendly label). */}
        <div>
          <span>Latest Activity</span>
          <strong>
            {display ? display.label : "None"}
          </strong>
        </div>

      </div>

    </div>
  );
}

// Export the AlertPanel component.
export default AlertPanel;
