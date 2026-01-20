"""
Preset CRUD API endpoints
"""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from models.preset import PresetConfig, PresetCreate, PresetUpdate, PresetCapture, ZoneSnapshot
from db.database import Database, get_db
from protocol import iTachConnection

router = APIRouter(prefix="/presets", tags=["presets"])

# Will be set by main app
_connection: Optional[iTachConnection] = None


def set_connection(conn: iTachConnection):
    """Set the iTach connection instance"""
    global _connection
    _connection = conn


def get_connection() -> iTachConnection:
    """Get the iTach connection instance"""
    if _connection is None:
        raise HTTPException(status_code=503, detail="iTach connection not available")
    return _connection


@router.get("", response_model=list[PresetConfig])
async def list_presets(db: Database = Depends(get_db)):
    """List all presets"""
    return await db.get_presets()


@router.get("/{preset_id}", response_model=PresetConfig)
async def get_preset(preset_id: UUID, db: Database = Depends(get_db)):
    """Get a preset by ID"""
    preset = await db.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.post("", response_model=PresetConfig, status_code=201)
async def create_preset(request: PresetCreate, db: Database = Depends(get_db)):
    """Create a new preset or update existing if ID provided"""
    # If ID provided (iOS sync), check if preset already exists
    if request.id:
        existing = await db.get_preset(request.id)
        if existing:
            # Update existing preset instead of creating duplicate
            existing.name = request.name
            existing.icon = request.icon
            existing.color = request.color
            existing.snapshots = request.snapshots
            return await db.update_preset(existing)

    # Create new preset (with provided ID or auto-generated)
    preset_data = {
        "name": request.name,
        "icon": request.icon,
        "color": request.color,
        "snapshots": request.snapshots,
    }
    if request.id:
        preset_data["id"] = request.id

    preset = PresetConfig(**preset_data)
    return await db.create_preset(preset)


@router.put("/{preset_id}", response_model=PresetConfig)
async def update_preset(
    preset_id: UUID,
    request: PresetUpdate,
    db: Database = Depends(get_db),
):
    """Update an existing preset"""
    preset = await db.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Update fields that were provided
    if request.name is not None:
        preset.name = request.name
    if request.icon is not None:
        preset.icon = request.icon
    if request.color is not None:
        preset.color = request.color
    if request.snapshots is not None:
        preset.snapshots = request.snapshots

    return await db.update_preset(preset)


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(preset_id: UUID, db: Database = Depends(get_db)):
    """Delete a preset"""
    success = await db.delete_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    return None


@router.post("/{preset_id}/apply")
async def apply_preset(
    preset_id: UUID,
    db: Database = Depends(get_db),
    conn: iTachConnection = Depends(get_connection),
):
    """Apply a preset to the audio system"""
    preset = await db.get_preset(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")

    # Apply each zone snapshot
    for snapshot in preset.snapshots:
        zone_id = snapshot.zone_id

        # Set power first
        await conn.set_power(zone_id, snapshot.power)

        if snapshot.power:
            # Only apply other settings if zone is on
            await conn.set_source(zone_id, snapshot.source)
            await conn.set_volume(zone_id, snapshot.volume)
            await conn.set_mute(zone_id, snapshot.mute)
            await conn.set_bass(zone_id, snapshot.bass)
            await conn.set_treble(zone_id, snapshot.treble)
            await conn.set_balance(zone_id, snapshot.balance)

    return {"success": True, "message": f"Preset '{preset.name}' applied"}


@router.post("/capture", response_model=PresetConfig, status_code=201)
async def capture_preset(
    request: PresetCapture,
    db: Database = Depends(get_db),
    conn: iTachConnection = Depends(get_connection),
):
    """Capture current zone states as a new preset"""
    # Query all zones
    states = await conn.query_all_zones()

    # Determine which zones to include
    if request.zones:
        # Specific zones requested
        zone_ids = set(request.zones)
    else:
        # All powered-on zones
        zone_ids = {z for z, state in states.items() if state.power}

    if not zone_ids:
        raise HTTPException(
            status_code=400,
            detail="No zones to capture (all zones are off)",
        )

    # Create snapshots
    snapshots = []
    for zone_id in sorted(zone_ids):
        state = states.get(zone_id)
        if state:
            snapshots.append(
                ZoneSnapshot(
                    zone_id=zone_id,
                    power=state.power,
                    source=state.source,
                    volume=state.volume,
                    mute=state.mute,
                    bass=state.bass,
                    treble=state.treble,
                    balance=state.balance,
                )
            )

    # Create preset
    preset = PresetConfig(
        name=request.name,
        icon=request.icon,
        color=request.color,
        snapshots=snapshots,
    )

    return await db.create_preset(preset)
