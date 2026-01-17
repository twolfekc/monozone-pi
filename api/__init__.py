"""
API endpoints for MonoZone Pi Controller
"""
from .zones import router as zones_router
from .schedules import router as schedules_router
from .presets import router as presets_router
from .status import router as status_router

__all__ = ["zones_router", "schedules_router", "presets_router", "status_router"]
