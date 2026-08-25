# PoolGuard Dashboard (pool-drowning-dashboard)

React (Vite) dashboard for the Swimming Pool Drowning Detection project. Shows the live camera feed, current safety status, rescue-device state with a manual emergency trigger, and the full detection history — all fed exclusively by the FastAPI backend over HTTP.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

Backend URL is configured once in `.env`:

```
VITE_API_URL=http://127.0.0.1:8000
```

Never hardcode the backend URL inside components (API contract §14).

## Architecture: the three frontend layers

```
pages/            Screens assembled from components (Dashboard, Events, ...)
    │
components/       UI pieces with state (CameraView, AlertPanel, RescuePanel, ...)
    │
    ▼
api/              ONLY place that talks to the network
    client.js         one base URL + shared request/error handling
    videoApi.js       /video/*
    detectionApi.js   /detection/*
    deviceApi.js      /device/*

utils/detectionDisplay.js   translates API values → UI values
                            (DROWNING → 🚨 "Drowning Detected", 0.93 → "93%")
```

Two rules keep this clean:

1. **Components never call `fetch()` directly.** They call an `api/` function. Swap the backend, add auth headers, or change error handling in one place.
2. **API values are never modified, only translated.** `DROWNING` stays `DROWNING` in every request/response; `detectionDisplay.js` converts it to a friendly label at render time. Same for confidence: the API keeps `0.93`, the UI shows `93%` (contract §8/§12).

## What each component does

| Component / Page | Data source | Behavior |
|---|---|---|
| `CameraView`   | GET /video/status + /video/frame | Polls every 3 s; shows frame only when backend says `connected`; cache-busts with `?t=timestamp` |
| `AlertPanel`   | GET /detection/latest | Polls every 5 s; turns red on a DROWNING event; treats 404 as "no events yet", not an error |
| `RescuePanel`  | GET /device/status, POST /device/emergency | Polls every 3 s; shows ESP32 online/offline + rod state; confirmation-guarded 🚨 Deploy button; surfaces 429 (cooldown) / 503 (device down) messages |
| `RecentEvents` | GET /detection | Newest 5 events with loading / empty / error states |
| `pages/Events` | GET /detection | Full table: date, time, device, event, confidence %, status, evidence-image link |

Polling pattern used everywhere: `useEffect` → immediate load → `setInterval` → **return a cleanup** that clears the interval. Forgetting the cleanup leaks timers when a component unmounts — every polling component here shows the correct pattern.

## Reading order (for learning)

1. `.env` + `src/api/client.js`
2. `src/api/videoApi.js` → `detectionApi.js` → `deviceApi.js`
3. `src/utils/detectionDisplay.js`
4. `components/StatusCard.jsx` (props only) → `RecentEvents.jsx` (fetching) → `AlertPanel.jsx` / `CameraView.jsx` (polling) → `RescuePanel.jsx` (actions)
5. `pages/Dashboard.jsx` → `App.jsx`

## Why this stack (short version — full comparison in the root README)

- **React** over Vue/Angular/plain JS: component model fits a multi-panel live dashboard, hooks handle polling cleanly, biggest ecosystem for getting help.
- **Vite** over Create React App: CRA is deprecated; Vite is instant and its `VITE_*` env handling is exactly what the one-base-URL rule needs.
- **fetch + plain state** over axios/Redux/React Query: at this size, the browser's `fetch` wrapped once in `client.js` and local `useState` are enough; adding state-management libraries now would be complexity with no payoff. (React Query would be the natural upgrade if polling logic grows.)

## Contract rules this frontend obeys

- Talks only to FastAPI — never to SQLite, RTSP, MQTT, the Pi, or the ESP32 (§3, §16, §17).
- No MQTT topics/credentials anywhere in this codebase (§17).
- snake_case field names untouched (§4).
- No mock data mixed with real calls — every panel is backend-driven (§17).
