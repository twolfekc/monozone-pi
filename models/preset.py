"""
Preset configuration models - matches iOS PresetConfig
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ZoneSnapshot(BaseModel):
    """Snapshot of a single zone's state"""

    zone_id: int = Field(..., ge=1, le=6)
    power: bool
    source: int = Field(..., ge=1, le=6)
    volume: int = Field(..., ge=0, le=38)
    mute: bool = False
    bass: int = Field(default=7, ge=0, le=14)
    treble: int = Field(default=7, ge=0, le=14)
    balance: int = Field(default=10, ge=0, le=20)

    class Config:
        json_schema_extra = {
            "example": {
                "zone_id": 1,
                "power": True,
                "source": 1,
                "volume": 20,
                "mute": False,
                "bass": 7,
                "treble": 7,
                "balance": 10,
            }
        }


class PresetConfig(BaseModel):
    """Complete preset configuration"""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(default="star.fill", description="SF Symbol name")
    color: str = Field(
        default="blue", description="Color name (blue, green, orange, etc.)"
    )
    snapshots: list[ZoneSnapshot] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Movie Night",
                "icon": "film",
                "color": "purple",
                "snapshots": [
                    {
                        "zone_id": 1,
                        "power": True,
                        "source": 3,
                        "volume": 25,
                        "mute": False,
                        "bass": 8,
                        "treble": 6,
                        "balance": 10,
                    }
                ],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        }


class PresetCreate(BaseModel):
    """Request body for creating a preset"""

    name: str = Field(..., min_length=1, max_length=100)
    icon: str = "star.fill"
    color: str = "blue"
    snapshots: list[ZoneSnapshot]


class PresetUpdate(BaseModel):
    """Request body for updating a preset"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    icon: Optional[str] = None
    color: Optional[str] = None
    snapshots: Optional[list[ZoneSnapshot]] = None


class PresetCapture(BaseModel):
    """Request body for capturing current state as preset"""

    name: str = Field(..., min_length=1, max_length=100)
    icon: str = "star.fill"
    color: str = "blue"
    zones: Optional[list[int]] = Field(
        default=None, description="Zone IDs to capture, or null for all powered zones"
    )
