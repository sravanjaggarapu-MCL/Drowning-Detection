// ============================================================
// FILE: RecentEvents.jsx
//
// PURPOSE:
// This component displays the most recent pool monitoring
// events on the dashboard.
//
// RESPONSIBILITIES:
// - Load detection history from the FastAPI backend.
// - Display the newest events (limited to a small number).
// - Translate API event types into friendly labels/icons.
// - Show loading, empty, and error states.
//
// DATA SOURCE:
//
// RecentEvents
//      |
//      v
// detectionApi.js ──► GET /detection ──► FastAPI ──► SQLite
//
// IMPORTANT:
// - This component does NOT call fetch() directly.
//   All backend communication goes through detectionApi.js.
// - API event types (DROWNING, SWIMMING, PERSON_DETECTED)
//   are translated for display in utils/detectionDisplay.js.
// - No mock data. The backend is the only data source.
// ============================================================


import { useEffect, useState } from "react";

import { getDetections } from "../api/detectionApi";

import {
  formatEventTime,
  getEventDisplay,
} from "../utils/detectionDisplay";


// Maximum number of events shown on the dashboard.
//
// The full history is available on the Events page.
const MAX_RECENT_EVENTS = 5;


// Create the RecentEvents component.
function RecentEvents() {

  // Detection events loaded from the backend.
  const [events, setEvents] = useState([]);

  // True while the first request is still running.
  const [loading, setLoading] = useState(true);

  // Error message when the backend request fails.
  const [error, setError] = useState(null);


  // ----------------------------------------------------------
  // LOAD EVENTS
  // ----------------------------------------------------------
  // Runs once when the component is mounted.
  //
  // GET /detection already returns newest-first (contract
  // section 9), so we only take the first few entries.
  // ----------------------------------------------------------

  useEffect(() => {

    async function loadEvents() {

      try {

        // Ask the backend for the full detection history.
        const detections = await getDetections();

        // Keep only the newest events for the dashboard.
        setEvents(detections.slice(0, MAX_RECENT_EVENTS));

        // Clear any previous error.
        setError(null);

      } catch (err) {

        // Store the error so the UI can show it.
        console.error("Unable to load recent events:", err);
        setError("Unable to load events from the backend.");

      } finally {

        // The first load attempt is finished either way.
        setLoading(false);
      }
    }

    // Run the initial load.
    loadEvents();

  }, []);


  // ----------------------------------------------------------
  // RENDER
  // ----------------------------------------------------------

  return (

    // Events container.
    <div className="recent-events">

      {/* Section heading. */}
      <div className="section-heading">

        {/* Title. */}
        <h2>Recent Events</h2>

        {/* View all button. */}
        <button className="text-button">
          View All
        </button>

      </div>

      {/* Event list. */}
      <div className="event-list">

        {/* Loading state (first request still running). */}
        {loading && (
          <p className="event-empty">Loading events...</p>
        )}

        {/* Error state (backend unreachable or failed). */}
        {!loading && error && (
          <p className="event-empty">{error}</p>
        )}

        {/* Empty state (backend reachable, no detections). */}
        {!loading && !error && events.length === 0 && (
          <p className="event-empty">No events recorded yet.</p>
        )}

        {/* Loop through each backend detection. */}
        {!loading && !error && events.map((event) => {

          // Translate the API event_type into display info.
          const display = getEventDisplay(event.event_type);

          return (

            // Individual event row.
            //
            // The database id is a stable unique key.
            <div className="event-row" key={event.id}>

              {/* Event icon. */}
              <div className="event-icon">
                {display.icon}
              </div>

              {/* Event information. */}
              <div className="event-details">

                {/* Friendly event name. */}
                <strong>{display.label}</strong>

                {/* Formatted event time. */}
                <span>{formatEventTime(event.timestamp)}</span>

              </div>

              {/* Event status badge. Dangerous events get an
                  extra CSS class so they appear in red. */}
              <span
                className={
                  `event-status ${display.danger ? "danger" : ""}`
                }
              >
                {display.status}
              </span>

            </div>
          );
        })}

      </div>

    </div>
  );
}

// Export the RecentEvents component.
export default RecentEvents;
