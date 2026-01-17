"""
Timer action models - matches iOS TimerAction
"""
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TimerActionType(str, Enum):
    """Types of actions that can be scheduled"""

    POWER_OFF = "power_off"
    POWER_ON = "power_on"
    SET_SOURCE = "set_source"
    SET_VOLUME = "set_volume"
    APPLY_PRESET = "apply_preset"

    @property
    def display_name(self) -> str:
        """Human-readable name"""
        return {
            TimerActionType.POWER_OFF: "Power Off",
            TimerActionType.POWER_ON: "Power On",
            TimerActionType.SET_SOURCE: "Set Source",
            TimerActionType.SET_VOLUME: "Set Volume",
            TimerActionType.APPLY_PRESET: "Apply Preset",
        }[self]

    @property
    def icon(self) -> str:
        """SF Symbol name for this action type"""
        return {
            TimerActionType.POWER_OFF: "power",
            TimerActionType.POWER_ON: "power",
            TimerActionType.SET_SOURCE: "music.note.list",
            TimerActionType.SET_VOLUME: "speaker.wave.2",
            TimerActionType.APPLY_PRESET: "star.fill",
        }[self]


class TimerAction(BaseModel):
    """Action to perform when schedule triggers"""

    type: TimerActionType
    source_id: Optional[int] = Field(
        default=None, ge=1, le=6, description="Source ID for SET_SOURCE action"
    )
    volume: Optional[int] = Field(
        default=None, ge=0, le=38, description="Volume for SET_VOLUME action"
    )
    preset_id: Optional[UUID] = Field(
        default=None, description="Preset ID for APPLY_PRESET action"
    )

    class Config:
        json_schema_extra = {
            "example": {"type": "power_off", "source_id": None, "volume": None}
        }


class TargetType(str, Enum):
    """Types of targets for timer actions"""

    ALL_ZONES = "all_zones"
    SPECIFIC_ZONES = "specific_zones"
    PRESET = "preset"


class TimerTarget(BaseModel):
    """Target zones for timer action"""

    type: TargetType
    zone_ids: Optional[set[int]] = Field(
        default=None, description="Zone IDs for SPECIFIC_ZONES target"
    )
    preset_id: Optional[UUID] = Field(
        default=None, description="Preset ID for PRESET target"
    )

    class Config:
        json_schema_extra = {"example": {"type": "all_zones", "zone_ids": None}}

    def get_zone_ids(self) -> set[int]:
        """Get the actual zone IDs based on target type"""
        if self.type == TargetType.ALL_ZONES:
            return {1, 2, 3, 4, 5, 6}
        elif self.type == TargetType.SPECIFIC_ZONES and self.zone_ids:
            return self.zone_ids
        return set()
