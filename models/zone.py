"""
Zone API models
"""
from pydantic import BaseModel, Field
from typing import Optional


class ZoneStateModel(BaseModel):
    """Zone state for API responses"""

    zone: int = Field(..., ge=1, le=6, description="Zone number (1-6)")
    power: bool = Field(..., description="Power state")
    volume: int = Field(..., ge=0, le=38, description="Volume level (0-38)")
    source: int = Field(..., ge=1, le=6, description="Source/channel (1-6)")
    mute: bool = Field(..., description="Mute state")
    bass: int = Field(..., ge=0, le=14, description="Bass level (0-14)")
    treble: int = Field(..., ge=0, le=14, description="Treble level (0-14)")
    balance: int = Field(..., ge=0, le=20, description="Balance (0-20)")
    pa: bool = Field(default=False, description="PA active")
    dnd: bool = Field(default=False, description="Do not disturb")
    keypad: bool = Field(default=False, description="Keypad active")

    class Config:
        json_schema_extra = {
            "example": {
                "zone": 1,
                "power": True,
                "volume": 20,
                "source": 1,
                "mute": False,
                "bass": 7,
                "treble": 7,
                "balance": 10,
                "pa": False,
                "dnd": False,
                "keypad": False,
            }
        }


class PowerRequest(BaseModel):
    """Request body for power control"""

    on: bool


class VolumeRequest(BaseModel):
    """Request body for volume control"""

    volume: int = Field(..., ge=0, le=38)


class SourceRequest(BaseModel):
    """Request body for source control"""

    source: int = Field(..., ge=1, le=6)


class MuteRequest(BaseModel):
    """Request body for mute control"""

    muted: bool


class BassRequest(BaseModel):
    """Request body for bass control"""

    bass: int = Field(..., ge=0, le=14)


class TrebleRequest(BaseModel):
    """Request body for treble control"""

    treble: int = Field(..., ge=0, le=14)


class BalanceRequest(BaseModel):
    """Request body for balance control"""

    balance: int = Field(..., ge=0, le=20)


class MultiZonePowerRequest(BaseModel):
    """Request body for multi-zone power control"""

    on: bool
    zones: Optional[list[int]] = Field(
        default=None, description="Zone IDs (1-6), or null for all"
    )
