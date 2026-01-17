"""
Status and health check endpoints
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(tags=["status"])

# Will be set by main app
_connection = None
_scheduler = None
_start_time: Optional[datetime] = None


def set_connection(conn):
    global _connection
    _connection = conn


def set_scheduler(scheduler):
    global _scheduler
    _scheduler = scheduler


def set_start_time(time: datetime):
    global _start_time
    _start_time = time


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class StatusResponse(BaseModel):
    status: str
    uptime_seconds: Optional[float]
    itach_connected: bool
    itach_host: Optional[str]
    itach_port: Optional[int]
    itach_last_error: Optional[str]
    scheduler_running: bool
    scheduled_jobs: int
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint"""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
    )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get detailed system status"""
    uptime = None
    if _start_time:
        uptime = (datetime.now() - _start_time).total_seconds()

    itach_connected = False
    itach_host = None
    itach_port = None
    itach_last_error = None

    if _connection:
        state = _connection.state
        itach_connected = state.connected
        itach_host = state.host
        itach_port = state.port
        itach_last_error = state.last_error

    scheduler_running = False
    scheduled_jobs = 0

    if _scheduler:
        scheduler_running = _scheduler.running
        scheduled_jobs = len(_scheduler.get_jobs())

    return StatusResponse(
        status="ok" if itach_connected else "degraded",
        uptime_seconds=uptime,
        itach_connected=itach_connected,
        itach_host=itach_host,
        itach_port=itach_port,
        itach_last_error=itach_last_error,
        scheduler_running=scheduler_running,
        scheduled_jobs=scheduled_jobs,
        timestamp=datetime.now().isoformat(),
    )


@router.post("/discover")
async def discover():
    """
    Return information for mDNS discovery.
    The iOS app can use this to find the Pi on the network.
    """
    import socket

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "unknown"

    return {
        "service": "monozone-pi",
        "version": "1.0.0",
        "hostname": hostname,
        "ip": local_ip,
        "port": 8080,
    }
