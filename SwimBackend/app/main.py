# ============================================================
# FILE: main.py
#
# PURPOSE:
# This is the main entry point of the PoolGuard FastAPI
# application (Swimming Pool Drowning Detection project).
#
# RESPONSIBILITIES:
# - Create the FastAPI application.
# - Initialize the database tables.
# - Enable CORS so the React frontend can call this API.
# - Start/stop the MQTT connection to the rescue device.
# - Register API routers.
# - Provide application-level endpoints.
#
# IMPORTANT:
# - Business logic does NOT belong here.
# - Video processing does NOT belong here.
# - Detection processing does NOT belong here.
# - MQTT logic belongs in services/mqtt_service.py.
# - Individual API endpoints belong inside routes/.
# ============================================================

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import engine
from app.models.detection import Base
from app.routes import detection
from app.routes import device
from app.routes import video
from app.services.mqtt_service import start_mqtt, stop_mqtt


# Create all database tables defined by our SQLAlchemy models.
#
# If the tables already exist, SQLAlchemy leaves them unchanged.
Base.metadata.create_all(bind=engine)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================
# The MQTT client must run for the whole lifetime of the
# backend so it can:
#
# - Receive ESP32 heartbeat/status messages continuously.
# - Publish rescue commands at any moment.
#
# FastAPI's lifespan context starts it on boot and stops it
# cleanly on shutdown.
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Connect to the MQTT broker in the background.
    #
    # If the broker is not running yet, the backend still
    # starts; paho-mqtt keeps retrying automatically.
    start_mqtt()

    # Hand control to the running application.
    yield

    # Disconnect cleanly when the server shuts down.
    stop_mqtt()


# Create the main FastAPI application instance.
app = FastAPI(
    title="PoolGuard API",
    description=(
        "Backend API for the Swimming Pool Drowning Detection "
        "system"
    ),
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================
# CORS (Cross-Origin Resource Sharing)
# ============================================================
# The React development server runs on a different origin
# (for example http://localhost:5173) than FastAPI
# (http://127.0.0.1:8000).
#
# Browsers block cross-origin requests unless the backend
# explicitly allows them. Without this middleware, every
# fetch() from React fails with a CORS error.
#
# Only local development origins are allowed. Production
# origins should be added here when deployment is planned.
# ============================================================

app.add_middleware(
    CORSMiddleware,

    # Origins that are allowed to call this API.
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    # Allow cookies/authorization headers if needed later.
    allow_credentials=True,

    # Allow all HTTP methods (GET, POST, ...).
    allow_methods=["*"],

    # Allow all request headers.
    allow_headers=["*"],
)


# Register the video API routes.
app.include_router(video.router)

# Register the detection API routes.
app.include_router(detection.router)

# Register the rescue device API routes.
app.include_router(device.router)


@app.get("/health")
def health():
    """
    Basic health-check endpoint.

    Used to verify that the backend is running.
    """

    return {
        "status": "ok",
        "message": "PoolGuard backend is running"
    }
