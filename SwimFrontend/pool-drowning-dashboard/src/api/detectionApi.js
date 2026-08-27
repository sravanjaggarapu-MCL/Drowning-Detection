// ============================================================
// FILE: detectionApi.js
//
// PURPOSE:
// Provides frontend functions for communicating with the
// FastAPI detection endpoints.
//
// RESPONSIBILITIES:
// - Create a detection event (with an optional image).
// - Get the detection history.
// - Get the latest detection.
// - Build the URL of a saved detection image.
//
// API ENDPOINTS USED:
//
// POST /detection
// GET  /detection
// GET  /detection/latest
// GET  /detection/image/{filename}
//
// ARCHITECTURE:
//
// React Component
//       |
//       v
// detectionApi.js
//       |
//       v
// client.js
//       |
//       | HTTP
//       v
// FastAPI
//       |
//       v
// Detection Service ──► SQLite + data/images/
//
// IMPORTANT:
// - This file does NOT contain UI code.
// - This file does NOT translate event types into labels
//   or icons. That belongs in utils/detectionDisplay.js.
// - API field names stay snake_case, exactly as defined in
//   the API contract. Do NOT rename them to camelCase.
// ============================================================


// ============================================================
// IMPORT COMMON API CLIENT
// ============================================================
//
// apiRequest() handles:
// - Backend URL
// - HTTP requests
// - HTTP error handling
//
// API_BASE_URL is used when we need a direct resource URL,
// such as a detection image URL for an <img> tag.
// ============================================================

import {
    apiRequest,
    API_BASE_URL
} from "./client";


// ============================================================
// CREATE DETECTION
// ============================================================
//
// Backend endpoint:
//
// POST /detection
// Content-Type: multipart/form-data
//
// Contract fields (section 7):
//
// device_id:  string   (required)
// event_type: string   (required)  DROWNING / SWIMMING /
//                                  PERSON_DETECTED
// confidence: float    (required)  0.0 to 1.0
// timestamp:  datetime (required)  ISO format
// image:      file     (optional)
//
// This function exists mainly for testing the backend from
// the frontend. In production, the Raspberry Pi will be the
// client that posts detections.
// ============================================================

export async function createDetection(
    {
        device_id,
        event_type,
        confidence,
        timestamp
    },
    imageFile = null
) {

    // The endpoint uses multipart/form-data because a file
    // can be included, so we build a FormData body.
    const formData = new FormData();

    // Field names MUST match the FastAPI Form(...) parameters.
    formData.append("device_id", device_id);
    formData.append("event_type", event_type);
    formData.append("confidence", confidence);
    formData.append("timestamp", timestamp);

    // Only append the image when one was actually provided,
    // because the field is optional in the contract.
    if (imageFile) {
        formData.append("image", imageFile);
    }

    // Send the detection to FastAPI.
    //
    // IMPORTANT:
    // Do NOT manually set Content-Type here. The browser
    // generates the correct multipart boundary automatically
    // when FormData is used.
    const response = await apiRequest(
        "/detection",
        {
            method: "POST",
            body: formData
        }
    );

    // Return the stored detection (including its new id).
    return response.json();
}


// ============================================================
// GET DETECTION HISTORY
// ============================================================
//
// Backend endpoint:
//
// GET /detection
//
// Returns an array of detections, newest first (section 9).
// ============================================================

export async function getDetections() {

    // Send the request to FastAPI.
    const response = await apiRequest(
        `/detection?t=${Date.now()}`,
        {
            cache: "no-store"
        }
    );

    // Convert the JSON response into a JavaScript array.
    return response.json();
}


// ============================================================
// GET LATEST DETECTION
// ============================================================
//
// Backend endpoint:
//
// GET /detection/latest
//
// Contract behavior (section 10):
// - 200 with the newest detection when one exists.
// - 404 when no detection has been recorded yet.
//
// A 404 is NOT an application failure here. It simply means
// the database is still empty, so this function returns
// null instead of throwing an error.
// ============================================================

export async function getLatestDetection() {

    try {

        // Send the request to FastAPI.
        const response = await apiRequest(
            `/detection/latest?t=${Date.now()}`,
            {
                cache: "no-store"
            }
        );

        // Return the newest detection object.
        return response.json();

    } catch (error) {

        // Treat "no detections yet" as a normal empty state.
        //
        // client.js throws with FastAPI's detail message,
        // so we detect the 404 case by its message.
        if (
            error.message.includes("404") ||
            error.message.includes("No detection")
        ) {
            return null;
        }

        // Any other error (backend down, 500, ...) is a real
        // problem and must be handled by the caller.
        throw error;
    }
}


// ============================================================
// GET DETECTION IMAGE URL
// ============================================================
//
// Backend endpoint:
//
// GET /detection/image/{filename}
//
// The endpoint returns an image file, not JSON, so we do not
// fetch it here. Instead we return the URL that the browser
// can use directly:
//
// <img src={getDetectionImageUrl(detection.image_filename)} />
// ============================================================

export function getDetectionImageUrl(filename) {

    // A detection without an image has image_filename = null.
    if (!filename) {
        return null;
    }

    // Construct the complete URL to the stored image.
    return `${API_BASE_URL}/detection/image/${filename}`;
}
