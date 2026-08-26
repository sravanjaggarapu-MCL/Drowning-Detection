// ============================================================
// FILE: CameraView.jsx
//
// PURPOSE:
// This component displays the live pool monitoring camera
// section of the PoolGuard dashboard.
//
// RESPONSIBILITIES:
// - Check the backend video status (contract section 6).
// - Display the latest video frame provided by FastAPI.
// - Refresh the frame periodically so the view stays live.
// - Display camera/AI monitoring status.
// - Preserve the existing PoolGuard camera UI.
//
// DATA SOURCE:
//
// React CameraView
//       |
//       v
// videoApi.js
//       |
//       v
// GET /video/status   → connected / disconnected / error
// GET /video/frame    → latest.jpg
//       |
//       v
// FastAPI ──► data/video/latest.jpg
//
// IMPORTANT:
// - This component does NOT connect directly to the RTSP camera.
// - This component does NOT run YOLO.
// - This component does NOT communicate with the Raspberry Pi.
// - The backend decides whether the video source is connected.
//   The frontend must not assume the camera is available
//   (contract section 6).
// - The existing UI/design is intentionally preserved.
// ============================================================


import { useEffect, useState } from "react";

import {
  getVideoFrameUrl,
  getVideoStatus,
} from "../api/videoApi";


// Keep status checks infrequent, while polling the latest frame
// often enough to make the development feed appear continuous.
const STATUS_REFRESH_INTERVAL_MS = 3000;
const FRAME_REFRESH_INTERVAL_MS = 200;


// ============================================================
// CAMERA VIEW COMPONENT
// ============================================================

function CameraView() {

  // ----------------------------------------------------------
  // VIDEO FRAME URL
  // ----------------------------------------------------------
  // Stores the URL of the latest frame provided by FastAPI.
  //
  // It stays null until the backend reports that the video
  // source is connected.
  // ----------------------------------------------------------

  const [frameUrl, setFrameUrl] = useState(null);


  // ----------------------------------------------------------
  // CAMERA STATUS
  // ----------------------------------------------------------
  // Follows the backend contract status values:
  // "connected", "disconnected", "error".
  // ----------------------------------------------------------

  const [cameraConnected, setCameraConnected] = useState(false);


  // ----------------------------------------------------------
  // LOAD VIDEO STATUS (WITH AUTO-REFRESH)
  // ----------------------------------------------------------
  //
  // This effect runs when the component is mounted and then
  // repeats on an interval, so the "live" view actually
  // updates when new frames arrive.
  //
  // Each cycle:
  // 1. Asks FastAPI for the video status.
  // 2. If connected, rebuilds the frame URL.
  //
  // The timestamp query parameter changes every cycle, which
  // prevents the browser from serving a cached latest.jpg.
  // ----------------------------------------------------------

  useEffect(() => {

    async function refreshCameraStatus() {

      try {

        // Call:
        //
        // GET /video/status
        //
        // Contract response example:
        //
        // { "status": "connected", "message": "..." }
        const videoStatus = await getVideoStatus();

        // Only "connected" means a frame is available.
        if (videoStatus.status === "connected") {

          setCameraConnected(true);

        } else {

          // "disconnected" or "error": no frame to show.
          setCameraConnected(false);
          setFrameUrl(null);
        }

      } catch (error) {

        // FastAPI itself is unreachable.
        console.error(
          "Unable to connect to video service:",
          error
        );

        setCameraConnected(false);
        setFrameUrl(null);
      }
    }


    // Run immediately on mount.
    refreshCameraStatus();

    // Then repeat on a fixed interval.

// Drowning detected
//       ↓
// Save JPG ✅
//       ↓
// Start 3-second cooldown
//       ↓
// Drowning detected again
//       ↓
// Ignore/save nothing ❌
//       ↓
// 3 seconds complete
//       ↓
// Can save another JPG

    const intervalId = setInterval(
      refreshCameraStatus,
      STATUS_REFRESH_INTERVAL_MS
    );

    // Stop refreshing when the component is removed.
    return () => clearInterval(intervalId);

  }, []);


  // Poll only the image at a higher rate. The timestamp prevents
  // the browser from reusing the previous latest.jpg response.
  useEffect(() => {

    if (!cameraConnected) {
      return undefined;
    }

    function refreshFrame() {
      setFrameUrl(`${getVideoFrameUrl()}?t=${Date.now()}`);
    }

    refreshFrame();
    const intervalId = setInterval(
      refreshFrame,
      FRAME_REFRESH_INTERVAL_MS
    );

    return () => clearInterval(intervalId);

  }, [cameraConnected]);


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    // Camera card container.
    <div className="camera-card">

      {/* Camera header. */}
      <div className="camera-header">

        {/* Camera title. */}
        <div>

          <h2>Live Pool Monitoring</h2>

          <p>
            Camera 01 • Main Swimming Pool
          </p>

        </div>


        {/* Live indicator. */}
        <div className="live-indicator">

          {/* Red live dot. */}
          <span></span>

          {/* Live text. */}
          LIVE

        </div>

      </div>


      {/* Camera image area. */}
      <div className="camera-screen">

        {frameUrl ? (

          // ----------------------------------------------------
          // BACKEND VIDEO FRAME
          // ----------------------------------------------------
          // Display the latest frame received from FastAPI.
          // ----------------------------------------------------

          <img
            src={frameUrl}
            alt="Swimming pool camera view"
          />

        ) : (

          // ----------------------------------------------------
          // NO FRAME AVAILABLE
          // ----------------------------------------------------
          // Display a simple message while the backend frame
          // is unavailable.
          // ----------------------------------------------------

          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <p>
              {cameraConnected
                ? "Waiting for video frame..."
                : "Camera unavailable"}
            </p>
          </div>

        )}


        {/* Camera overlay. */}
        <div className="camera-overlay">

          {/* Camera identifier. */}
          <span>
            CAM 01
          </span>

          {/* Monitoring message. */}
          <span>
            {cameraConnected
              ? "Monitoring Active"
              : "Camera Offline"}
          </span>

        </div>

      </div>


      {/* Camera footer. */}
      <div className="camera-footer">

        {/* AI monitoring status. */}
        <div>

          <span className="status-dot green"></span>

          AI Detection Active

        </div>


        {/* Camera connection status. */}
        <div>

          {cameraConnected
            ? "Camera Connected"
            : "Camera Disconnected"}

        </div>

      </div>

    </div>
  );
}


// ============================================================
// EXPORT COMPONENT
// ============================================================

export default CameraView;
