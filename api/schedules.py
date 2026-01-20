"""
Schedule CRUD API endpoints
"""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends

from models.schedule import ScheduleConfig, ScheduleCreate, ScheduleUpdate
from db.database import Database, get_db

router = APIRouter(prefix="/schedules", tags=["schedules"])

# Will be set by main app to trigger scheduler updates
_on_schedule_change = None


def set_schedule_change_callback(callback):
    """Set callback for when schedules change"""
    global _on_schedule_change
    _on_schedule_change = callback


@router.get("", response_model=list[ScheduleConfig])
async def list_schedules(db: Database = Depends(get_db)):
    """List all schedules"""
    return await db.get_schedules()


@router.get("/{schedule_id}", response_model=ScheduleConfig)
async def get_schedule(schedule_id: UUID, db: Database = Depends(get_db)):
    """Get a schedule by ID"""
    schedule = await db.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("", response_model=ScheduleConfig, status_code=201)
async def create_schedule(request: ScheduleCreate, db: Database = Depends(get_db)):
    """Create a new schedule"""
    # Validate weekdays
    if not request.weekdays:
        raise HTTPException(status_code=400, detail="At least one weekday required")
    for day in request.weekdays:
        if not 1 <= day <= 7:
            raise HTTPException(status_code=400, detail="Weekdays must be 1-7")

    # If ID provided (iOS sync), check if schedule already exists
    if request.id:
        existing = await db.get_schedule(request.id)
        if existing:
            # Update existing schedule instead of creating duplicate
            existing.name = request.name
            existing.is_enabled = request.is_enabled
            existing.time = request.time
            existing.weekdays = request.weekdays
            existing.target = request.target
            existing.action = request.action
            result = await db.update_schedule(existing)

            if _on_schedule_change:
                await _on_schedule_change()

            return result

    # Create new schedule (with provided ID or auto-generated)
    schedule_data = {
        "name": request.name,
        "is_enabled": request.is_enabled,
        "time": request.time,
        "weekdays": request.weekdays,
        "target": request.target,
        "action": request.action,
    }
    if request.id:
        schedule_data["id"] = request.id

    schedule = ScheduleConfig(**schedule_data)

    result = await db.create_schedule(schedule)

    # Notify scheduler of change
    if _on_schedule_change:
        await _on_schedule_change()

    return result


@router.put("/{schedule_id}", response_model=ScheduleConfig)
async def update_schedule(
    schedule_id: UUID,
    request: ScheduleUpdate,
    db: Database = Depends(get_db),
):
    """Update an existing schedule"""
    schedule = await db.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields that were provided
    if request.name is not None:
        schedule.name = request.name
    if request.time is not None:
        schedule.time = request.time
    if request.weekdays is not None:
        if not request.weekdays:
            raise HTTPException(status_code=400, detail="At least one weekday required")
        for day in request.weekdays:
            if not 1 <= day <= 7:
                raise HTTPException(status_code=400, detail="Weekdays must be 1-7")
        schedule.weekdays = request.weekdays
    if request.target is not None:
        schedule.target = request.target
    if request.action is not None:
        schedule.action = request.action
    if request.is_enabled is not None:
        schedule.is_enabled = request.is_enabled

    result = await db.update_schedule(schedule)

    # Notify scheduler of change
    if _on_schedule_change:
        await _on_schedule_change()

    return result


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: UUID, db: Database = Depends(get_db)):
    """Delete a schedule"""
    success = await db.delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Notify scheduler of change
    if _on_schedule_change:
        await _on_schedule_change()

    return None


@router.post("/{schedule_id}/toggle", response_model=ScheduleConfig)
async def toggle_schedule(
    schedule_id: UUID,
    enabled: bool,
    db: Database = Depends(get_db),
):
    """Enable or disable a schedule"""
    schedule = await db.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.is_enabled = enabled
    result = await db.update_schedule(schedule)

    # Notify scheduler of change
    if _on_schedule_change:
        await _on_schedule_change()

    return result


@router.post("/{schedule_id}/run")
async def run_schedule(schedule_id: UUID, db: Database = Depends(get_db)):
    """Execute a schedule immediately"""
    schedule = await db.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Import here to avoid circular dependency
    from scheduler.executor import execute_schedule

    await execute_schedule(schedule)

    return {"success": True, "message": f"Schedule '{schedule.name}' executed"}
