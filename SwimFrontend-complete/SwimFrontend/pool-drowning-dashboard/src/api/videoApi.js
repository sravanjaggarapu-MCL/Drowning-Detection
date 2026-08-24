// ============================================================
// FILE: videoApi.js
//
// PURPOSE:
// Provides frontend functions for communicating with the
// FastAPI video endpoints.
//
// RESPONSIBILITIES:
// - Get the current video service status.
// - Get the latest video frame.
// - Upload a video frame when required.
//
// API ENDPOINTS USED:
//
// GET  /video/status
// POST /video/frame
// GET  /video/frame
//
// ARCHITECTURE:
//
// React Component
//       |
//       v
// videoApi.js
//       |
//       v
// client.js
//       |
//       | HTTP
//       v
// FastAPI
//       |
//       v
// Video Service
//
// IMPORTANT:
// - This file does NOT contain UI code.
// - This file does NOT contain React components.
// - This file does NOT contain RTSP logic.
// - This file does NOT run YOLO.
// - The Raspberry Pi will eventually be responsible for
//   camera/YOLO processing.
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
// API_BASE_URL is used when we need to construct a direct
// resource URL, such as the image URL.
// ============================================================

import {
    apiRequest,
    API_BASE_URL
} from "./client";


// ============================================================
// GET VIDEO STATUS
// ============================================================
//
// Backend endpoint:
//
// GET /video/status
//
// Example response:
//
// {
//     "status": "video service is running"
// }
// ============================================================

export async function getVideoStatus() {

    // Send the request to FastAPI.
    const response = await apiRequest(
        "/video/status"
    );

    // Convert FastAPI's JSON response into a JavaScript
    // object and return it to the React component.
    return response.json();
}


// ============================================================
// GET LATEST VIDEO FRAME URL
// ============================================================
//
// Backend endpoint:
//
// GET /video/frame
//
// Unlike normal JSON API calls, the endpoint returns an image.
//
// We therefore don't call response.json() here.
//
// Instead, we return the URL that the browser can use as
// an image source.
//
// Example:
//
// <img src={getVideoFrameUrl()} />
// ============================================================

export function getVideoFrameUrl() {

    // Construct the complete URL to the latest frame.
    return `${API_BASE_URL}/video/frame`;
}


// ============================================================
// UPLOAD VIDEO FRAME
// ============================================================
//
// Backend endpoint:
//
// POST /video/frame
//
// The backend expects:
//
// Content-Type: multipart/form-data
//
// with:
//
// frame: <image file>
//
// This function is useful for testing the backend from the
// frontend and will also be useful later if another client
// needs to send frames to FastAPI.
// ============================================================

export async function uploadVideoFrame(
    frameFile
) {

    // Create a multipart/form-data body.
    const formData = new FormData();

    // The field name MUST match the FastAPI parameter:
    //
    // frame: UploadFile = File(...)
    //
    // Therefore the field must be named "frame".
    formData.append(
        "frame",
        frameFile
    );

    // Send the image to FastAPI.
    //
    // IMPORTANT:
    // Do NOT manually set Content-Type here.
    //
    // The browser automatically creates the correct
    // multipart/form-data boundary when FormData is used.
    const response = await apiRequest(
        "/video/frame",
        {
            method: "POST",
            body: formData
        }
    );

    // Return FastAPI's JSON response.
    return response.json();
}