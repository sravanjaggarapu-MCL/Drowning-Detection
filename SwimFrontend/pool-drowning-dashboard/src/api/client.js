// ============================================================
// FILE: client.js
//
// PURPOSE:
// Provides the common HTTP client configuration used by the
// React frontend when communicating with the FastAPI backend.
//
// RESPONSIBILITIES:
// - Read the FastAPI URL from the Vite environment.
// - Provide a common function for making API requests.
// - Keep the backend URL in one place.
//
// ARCHITECTURE:
//
// React Component
//       |
//       v
// API function
//       |
//       v
// client.js
//       |
//       | HTTP
//       v
// FastAPI
//
// IMPORTANT:
// - This file does NOT contain feature-specific API functions.
// - Video API functions are in videoApi.js.
// - Detection API functions will be in detectionApi.js.
// - Do not hardcode the FastAPI URL inside components.
// ============================================================


// ============================================================
// BACKEND BASE URL
// ============================================================
//
// Vite exposes variables beginning with VITE_.
//
// Expected .env:
//
// VITE_API_URL=http://127.0.0.1:8000
//
// The fallback below prevents the entire React application
// from crashing if the .env file is temporarily unavailable.
// ============================================================

const API_BASE_URL =
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000";


// ============================================================
// API REQUEST FUNCTION
// ============================================================
//
// This is the common HTTP function used by the API layer.
//
// Example:
//
// apiRequest("/health")
//
// becomes:
//
// GET http://127.0.0.1:8000/health
// ============================================================

export async function apiRequest(
    endpoint,
    options = {}
) {

// Make sure the endpoint starts with "/".
//     Does endpoint start with "/"?

//           ↙              ↘

//         YES               NO

//          ↓                 ↓

//    Keep endpoint      Add "/" before it
 

    const normalizedEndpoint = endpoint.startsWith("/")
        ? endpoint 
        : `/${endpoint}`; 

    // Build the complete backend URL.
    const url =
        `${API_BASE_URL}${normalizedEndpoint}`;

    // Send the request to FastAPI.
    const response = await fetch(
        url,
        options
    );

    // Handle HTTP errors.
    //
    // Examples:
    // 404 → resource not found
    // 422 → validation error
    // 500 → backend error
    if (!response.ok) {

        let errorMessage =
            `API request failed: ${response.status}`;

        // Try to read FastAPI's error response.
        try {

            const errorData =
                await response.json();

            if (errorData.detail) {
                errorMessage = errorData.detail;
            }

        } catch {
            // Keep the default HTTP error message if the
            // response is not valid JSON.
        }

        throw new Error(errorMessage);
    }

    // Return the raw Response object.
    //
    // Individual API modules decide whether to use:
    // response.json()
    // response.blob()
    // etc.
    return response;
}


// ============================================================
// EXPORT BACKEND URL
// ============================================================
//
// Other frontend modules can use this when they need a direct
// URL to a backend resource.
//
// Example:
//
// `${API_BASE_URL}/video/frame`
// ============================================================

export {
    API_BASE_URL
};