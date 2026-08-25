// ============================================================
// FILE: Events.jsx
//
// PURPOSE:
// This page displays the full pool monitoring event history.
//
// RESPONSIBILITIES:
// - Load the complete detection history from the backend.
// - Display date, time, device, event, confidence, status,
//   and a link to the evidence image when one exists.
// - Show loading, empty, and error states.
//
// DATA SOURCE:
//
// Events page
//      |
//      v
// detectionApi.js ──► GET /detection ──► FastAPI ──► SQLite
//                     GET /detection/image/{filename}
//                          (evidence image links)
//
// IMPORTANT:
// - This page does NOT call fetch() directly.
//   All backend communication goes through detectionApi.js.
// - The API returns confidence as 0.0–1.0. The percentage
//   conversion happens only for display (contract section 12).
// - No mock data. The backend is the only data source.
// ============================================================


import { useEffect, useState } from "react";

import {
  getDetections,
  getDetectionImageUrl,
} from "../api/detectionApi";

import {
  formatConfidence,
  formatEventDate,
  formatEventTime,
  getEventDisplay,
} from "../utils/detectionDisplay";


// Create the Events component.
function Events() {

  // Detection events loaded from the backend.
  const [events, setEvents] = useState([]);

  // True while the first request is still running.
  const [loading, setLoading] = useState(true);

  // Error message when the backend request fails.
  const [error, setError] = useState(null);


  // ----------------------------------------------------------
  // LOAD EVENTS
  // ----------------------------------------------------------
  // Runs once when the page is opened.
  //
  // GET /detection returns the history newest-first
  // (contract section 9), so no extra sorting is needed.
  // ----------------------------------------------------------

  useEffect(() => {

    async function loadEvents() {

      try {

        // Ask the backend for the full detection history.
        const detections = await getDetections();

        // Store the backend result.
        setEvents(detections);

        // Clear any previous error.
        setError(null);

      } catch (err) {

        // Store the error so the UI can show it.
        console.error("Unable to load events:", err);
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

    // Main page container.
    <main className="page-container">

      {/* Page heading. */}
      <section className="page-heading">

        {/* Page title. */}
        <h1>Monitoring Events</h1>

        {/* Page description. */}
        <p>
          View recent activity detected by the pool monitoring system.
        </p>

      </section>

      {/* Events card. */}
      <div className="events-card">

        {/* Loading state. */}
        {loading && (
          <p className="event-empty">Loading events...</p>
        )}

        {/* Error state. */}
        {!loading && error && (
          <p className="event-empty">{error}</p>
        )}

        {/* Empty state. */}
        {!loading && !error && events.length === 0 && (
          <p className="event-empty">
            No events have been recorded yet.
          </p>
        )}

        {/* Events table (only when data exists). */}
        {!loading && !error && events.length > 0 && (

          // Events table wrapper.
          <div className="table-wrapper">

            {/* Events table. */}
            <table>

              {/* Table heading. */}
              <thead>

                {/* Header row. */}
                <tr>

                  {/* Date column. */}
                  <th>Date</th>

                  {/* Time column. */}
                  <th>Time</th>

                  {/* Device column (from device_id). */}
                  <th>Device</th>

                  {/* Event column. */}
                  <th>Event</th>

                  {/* Confidence column. */}
                  <th>Confidence</th>

                  {/* Status column. */}
                  <th>Status</th>

                  {/* Evidence image column. */}
                  <th>Image</th>

                </tr>

              </thead>

              {/* Table body. */}
              <tbody>

                {/* Display every backend detection. */}
                {events.map((event) => {

                  // Translate API values into display info.
                  const display = getEventDisplay(event.event_type);

                  // Build the evidence image URL, or null when
                  // the detection has no image.
                  const imageUrl = getDetectionImageUrl(
                    event.image_filename
                  );

                  return (

                    // Event table row (database id as key).
                    <tr key={event.id}>

                      {/* Formatted date. */}
                      <td>{formatEventDate(event.timestamp)}</td>

                      {/* Formatted time. */}
                      <td>{formatEventTime(event.timestamp)}</td>

                      {/* Device that produced the detection. */}
                      <td>{event.device_id}</td>

                      {/* Friendly event name. */}
                      <td>
                        {display.icon} {display.label}
                      </td>

                      {/* Confidence shown as a percentage.
                          The API value itself stays 0.0–1.0. */}
                      <td>{formatConfidence(event.confidence)}</td>

                      {/* Event status badge. */}
                      <td>
                        <span
                          className={
                            `table-status ${display.danger ? "danger" : ""}`
                          }
                        >
                          {display.status}
                        </span>
                      </td>

                      {/* Evidence image link (optional field). */}
                      <td>
                        {imageUrl ? (
                          <a
                            href={imageUrl}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View
                          </a>
                        ) : (
                          <span>—</span>
                        )}
                      </td>

                    </tr>
                  );
                })}

              </tbody>

            </table>

          </div>

        )}

      </div>

    </main>
  );
}

// Export the Events component.
export default Events;
