"""
Zone control API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from models.zone import (
    ZoneStateModel,
    PowerRequest,
    VolumeRequest,
    SourceRequest,
    MuteRequest,
    BassRequest,
    TrebleRequest,
    BalanceRequest,
    MultiZonePowerRequest,
)
from protocol import iTachConnection

router = APIRouter(prefix="/zones", tags=["zones"])

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


@router.get("", response_model=list[ZoneStateModel])
async def get_all_zones(conn: iTachConnection = Depends(get_connection)):
    """Get state of all zones"""
    states = await conn.query_all_zones()
    return [
        ZoneStateModel(**state.to_dict())
        for state in states.values()
    ]


@router.get("/{zone_id}", response_model=ZoneStateModel)
async def get_zone(zone_id: int, conn: iTachConnection = Depends(get_connection)):
    """Get state of a single zone"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    state = await conn.query_zone(zone_id)
    if state is None:
        raise HTTPException(status_code=502, detail="Failed to query zone")

    return ZoneStateModel(**state.to_dict())


@router.post("/{zone_id}/power")
async def set_power(
    zone_id: int,
    request: PowerRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone power on/off"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_power(zone_id, request.on)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set power")

    return {"success": True, "zone": zone_id, "power": request.on}


@router.post("/{zone_id}/volume")
async def set_volume(
    zone_id: int,
    request: VolumeRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone volume (0-38)"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_volume(zone_id, request.volume)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set volume")

    return {"success": True, "zone": zone_id, "volume": request.volume}


@router.post("/{zone_id}/source")
async def set_source(
    zone_id: int,
    request: SourceRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone source (1-6)"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_source(zone_id, request.source)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set source")

    return {"success": True, "zone": zone_id, "source": request.source}


@router.post("/{zone_id}/mute")
async def set_mute(
    zone_id: int,
    request: MuteRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone mute on/off"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_mute(zone_id, request.muted)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set mute")

    return {"success": True, "zone": zone_id, "mute": request.muted}


@router.post("/{zone_id}/bass")
async def set_bass(
    zone_id: int,
    request: BassRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone bass (0-14)"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_bass(zone_id, request.bass)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set bass")

    return {"success": True, "zone": zone_id, "bass": request.bass}


@router.post("/{zone_id}/treble")
async def set_treble(
    zone_id: int,
    request: TrebleRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone treble (0-14)"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_treble(zone_id, request.treble)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set treble")

    return {"success": True, "zone": zone_id, "treble": request.treble}


@router.post("/{zone_id}/balance")
async def set_balance(
    zone_id: int,
    request: BalanceRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set zone balance (0-20)"""
    if not 1 <= zone_id <= 6:
        raise HTTPException(status_code=400, detail="Zone ID must be 1-6")

    success = await conn.set_balance(zone_id, request.balance)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set balance")

    return {"success": True, "zone": zone_id, "balance": request.balance}


@router.post("/all/power")
async def set_all_power(
    request: MultiZonePowerRequest,
    conn: iTachConnection = Depends(get_connection),
):
    """Set power for multiple zones at once"""
    zones = request.zones
    if zones:
        for z in zones:
            if not 1 <= z <= 6:
                raise HTTPException(status_code=400, detail="Zone IDs must be 1-6")

    success = await conn.set_all_power(request.on, zones)
    if not success:
        raise HTTPException(status_code=502, detail="Failed to set power for some zones")

    return {
        "success": True,
        "zones": zones or list(range(1, 7)),
        "power": request.on,
    }
