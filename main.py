"""
MonoZone Pi Controller - Main Application

REST API server for controlling Monoprice 6-Zone Audio via iTach Flex.
Includes scheduling support for automated zone control.

GitHub: https://github.com/twolfekc/monozone-pi
"""
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import config
from protocol import iTachConnection
from db.database import init_db, close_db, get_db
from scheduler.executor import ScheduleExecutor, set_executor
from api import zones_router, schedules_router, presets_router, status_router
from api.zones import set_connection as set_zones_connection
from api.presets import set_connection as set_presets_connection
from api.schedules import set_schedule_change_callback
from api.status import set_connection as set_status_connection, set_scheduler, set_start_time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
connection: iTachConnection = None
executor: ScheduleExecutor = None


async def poll_zones():
    """Background task to poll zone states periodically"""
    while config.POLL_ENABLED:
        try:
            if connection and connection.is_connected:
                await connection.query_all_zones()
        except Exception as e:
            logger.warning(f"Poll error: {e}")

        await asyncio.sleep(config.POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global connection, executor

    logger.info("Starting MonoZone Pi Controller")
    set_start_time(datetime.now())

    # Initialize database
    logger.info(f"Initializing database at {config.DB_PATH}")
    db = await init_db(config.DB_PATH)

    # Initialize iTach connection
    logger.info(f"Connecting to iTach at {config.ITACH_HOST}:{config.ITACH_PORT}")
    connection = iTachConnection(
        host=config.ITACH_HOST,
        port=config.ITACH_PORT,
        timeout=config.ITACH_TIMEOUT,
        reconnect_delay=config.ITACH_RECONNECT_DELAY,
    )

    # Set up connection callbacks
    def on_connection_change(connected: bool):
        status = "connected" if connected else "disconnected"
        logger.info(f"iTach {status}")

    connection.on_connection_change(on_connection_change)

    # Try initial connection
    await connection.connect()

    # Initialize scheduler
    logger.info("Initializing scheduler")
    executor = ScheduleExecutor(connection, db)
    set_executor(executor)
    await executor.start()

    # Set up API dependencies
    set_zones_connection(connection)
    set_presets_connection(connection)
    set_status_connection(connection)
    set_scheduler(executor.scheduler)

    # Set up schedule change callback
    async def on_schedule_change():
        await executor.reload_schedules()

    set_schedule_change_callback(on_schedule_change)

    # Start background polling task
    poll_task = asyncio.create_task(poll_zones())

    logger.info(f"MonoZone Pi Controller started on port {config.API_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down MonoZone Pi Controller")

    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass

    await executor.stop()
    await connection.disconnect()
    await close_db()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MonoZone Pi Controller",
    description="REST API for controlling Monoprice 6-Zone Audio Controller via iTach Flex",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware (allow iOS app to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(zones_router, prefix="/api")
app.include_router(schedules_router, prefix="/api")
app.include_router(presets_router, prefix="/api")
app.include_router(status_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MonoZone Pi Controller",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "/api/status",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
    )
