"""
Schedule configuration models - matches iOS ScheduleConfig
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from .action import TimerAction, TimerTarget


class ScheduleTime(BaseModel):
    """Time of day for schedule"""

    hour: int = Field(..., ge=0, le=23, description="Hour (0-23)")
    minute: int = Field(..., ge=0, le=59, description="Minute (0-59)")

    @property
    def display_string(self) -> str:
        """Format as HH:MM AM/PM"""
        hour_12 = self.hour % 12 or 12
        period = "AM" if self.hour < 12 else "PM"
        return f"{hour_12}:{self.minute:02d} {period}"

    class Config:
        json_schema_extra = {"example": {"hour": 22, "minute": 30}}


class ScheduleConfig(BaseModel):
    """Complete schedule configuration"""

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    is_enabled: bool = Field(default=True)
    time: ScheduleTime
    weekdays: set[int] = Field(
        ..., description="Weekdays (1=Sunday, 2=Monday, ..., 7=Saturday)"
    )
    target: TimerTarget
    action: TimerAction
    created_at: datetime = Field(default_factory=datetime.now)
    last_triggered_at: Optional[datetime] = None

    @property
    def weekdays_display_string(self) -> str:
        """Format weekdays for display"""
        if self.weekdays == {1, 2, 3, 4, 5, 6, 7}:
            return "Every day"
        if self.weekdays == {2, 3, 4, 5, 6}:
            return "Weekdays"
        if self.weekdays == {1, 7}:
            return "Weekends"

        day_names = {
            1: "Sun",
            2: "Mon",
            3: "Tue",
            4: "Wed",
            5: "Thu",
            6: "Fri",
            7: "Sat",
        }
        sorted_days = sorted(self.weekdays)
        return ", ".join(day_names[d] for d in sorted_days)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Bedtime",
                "is_enabled": True,
                "time": {"hour": 22, "minute": 30},
                "weekdays": [1, 2, 3, 4, 5, 6, 7],
                "target": {"type": "all_zones"},
                "action": {"type": "power_off"},
                "created_at": "2024-01-01T00:00:00",
                "last_triggered_at": None,
            }
        }


class ScheduleCreate(BaseModel):
    """Request body for creating a schedule"""

    name: str = Field(..., min_length=1, max_length=100)
    time: ScheduleTime
    weekdays: set[int]
    target: TimerTarget
    action: TimerAction
    is_enabled: bool = True


class ScheduleUpdate(BaseModel):
    """Request body for updating a schedule"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    time: Optional[ScheduleTime] = None
    weekdays: Optional[set[int]] = None
    target: Optional[TimerTarget] = None
    action: Optional[TimerAction] = None
    is_enabled: Optional[bool] = None
