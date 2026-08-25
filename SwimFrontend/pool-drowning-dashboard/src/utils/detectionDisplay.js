// ============================================================
// FILE: detectionDisplay.js
//
// PURPOSE:
// Translates raw API detection values into user-friendly
// display information (labels, icons, status text).
//
// RESPONSIBILITIES:
// - Map API event_type values to friendly labels and icons.
// - Decide whether an event is dangerous or normal.
// - Format API timestamps for display.
// - Format API confidence values for display.
//
// ARCHITECTURE:
//
// FastAPI ──► detectionApi.js ──► React component
//                                      |
//                                      v
//                             detectionDisplay.js
//                             (API value → UI value)
//
// IMPORTANT:
// - The API values DROWNING / SWIMMING / PERSON_DETECTED
//   are part of the API contract (section 8) and must stay
//   stable. Only their DISPLAY may be translated here.
// - The API stores confidence as 0.0–1.0 (section 12).
//   The percentage conversion happens ONLY in the UI layer.
// - This file contains no React components and no API calls.
// ============================================================


// ============================================================
// EVENT TYPE DISPLAY TABLE
// ============================================================
//
// One entry per contract event type.
//
// label:    Friendly text shown to the user.
// icon:     Emoji shown next to the event.
// danger:   Whether the event represents an emergency.
// status:   Short status word used in badges/tables.
// ============================================================

const EVENT_DISPLAY = {

    // Emergency event: a possible drowning was detected.
    DROWNING: {
        label: "Drowning Detected",
        icon: "🚨",
        danger: true,
        status: "Danger"
    },

    // Normal activity: someone is swimming.
    SWIMMING: {
        label: "Swimming Activity",
        icon: "🏊",
        danger: false,
        status: "Normal"
    },

    // Normal activity: a person is near/in the pool area.
    PERSON_DETECTED: {
        label: "Person Detected",
        icon: "👤",
        danger: false,
        status: "Normal"
    }
};


// ============================================================
// GET EVENT DISPLAY
// ============================================================

export function getEventDisplay(eventType) {

    // Return the mapped display entry when the event type
    // is one of the agreed contract values.
    if (EVENT_DISPLAY[eventType]) {
        return EVENT_DISPLAY[eventType];
    }

    // Unknown event types can appear if the backend adds a
    // new type before the frontend is updated. Show the raw
    // value instead of crashing the UI.
    return {
        label: eventType,
        icon: "❓",
        danger: false,
        status: "Unknown"
    };
}


// ============================================================
// FORMAT TIMESTAMP
// ============================================================
//
// The API sends ISO-style datetimes such as:
//
// "2026-08-22T14:30:00"
//
// The contract (section 12) says the frontend formats the
// timestamp for display.
// ============================================================

export function formatEventDate(timestamp) {

    // Convert the ISO string into a Date object.
    const date = new Date(timestamp);

    // Example output: "22 Aug 2026"
    return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}


export function formatEventTime(timestamp) {

    // Convert the ISO string into a Date object.
    const date = new Date(timestamp);

    // Example output: "02:30 PM"
    return date.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit"
    });
}


// ============================================================
// FORMAT CONFIDENCE
// ============================================================
//
// The API stores confidence as 0.0–1.0 (e.g. 0.91).
// The UI displays it as a percentage (e.g. "91%").
// The stored value is never changed.
// ============================================================

export function formatConfidence(confidence) {

    // Convert 0.91 → "91%".
    return `${Math.round(confidence * 100)}%`;
}
