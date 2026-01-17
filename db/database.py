"""
SQLite database for schedule and preset persistence
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID
import aiosqlite

from models.schedule import ScheduleConfig, ScheduleTime
from models.preset import PresetConfig, ZoneSnapshot
from models.action import TimerAction, TimerTarget

logger = logging.getLogger(__name__)


class Database:
    """Async SQLite database for schedules and presets"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Open database connection and create tables"""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info(f"Connected to database: {self.db_path}")

    async def close(self):
        """Close database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self):
        """Create database tables if they don't exist"""
        await self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                weekdays TEXT NOT NULL,
                target_json TEXT NOT NULL,
                action_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_triggered_at TEXT
            );

            CREATE TABLE IF NOT EXISTS presets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT 'star.fill',
                color TEXT NOT NULL DEFAULT 'blue',
                snapshots_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(is_enabled);
            CREATE INDEX IF NOT EXISTS idx_presets_name ON presets(name);
        """
        )
        await self._conn.commit()

    # Schedule Operations

    async def get_schedules(self) -> list[ScheduleConfig]:
        """Get all schedules"""
        cursor = await self._conn.execute("SELECT * FROM schedules ORDER BY hour, minute")
        rows = await cursor.fetchall()
        return [self._row_to_schedule(row) for row in rows]

    async def get_schedule(self, schedule_id: UUID) -> Optional[ScheduleConfig]:
        """Get a schedule by ID"""
        cursor = await self._conn.execute(
            "SELECT * FROM schedules WHERE id = ?", (str(schedule_id),)
        )
        row = await cursor.fetchone()
        return self._row_to_schedule(row) if row else None

    async def create_schedule(self, schedule: ScheduleConfig) -> ScheduleConfig:
        """Create a new schedule"""
        await self._conn.execute(
            """
            INSERT INTO schedules (id, name, is_enabled, hour, minute, weekdays,
                                   target_json, action_json, created_at, last_triggered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(schedule.id),
                schedule.name,
                1 if schedule.is_enabled else 0,
                schedule.time.hour,
                schedule.time.minute,
                json.dumps(list(schedule.weekdays)),
                schedule.target.model_dump_json(),
                schedule.action.model_dump_json(),
                schedule.created_at.isoformat(),
                schedule.last_triggered_at.isoformat()
                if schedule.last_triggered_at
                else None,
            ),
        )
        await self._conn.commit()
        return schedule

    async def update_schedule(self, schedule: ScheduleConfig) -> ScheduleConfig:
        """Update an existing schedule"""
        await self._conn.execute(
            """
            UPDATE schedules SET
                name = ?, is_enabled = ?, hour = ?, minute = ?, weekdays = ?,
                target_json = ?, action_json = ?, last_triggered_at = ?
            WHERE id = ?
            """,
            (
                schedule.name,
                1 if schedule.is_enabled else 0,
                schedule.time.hour,
                schedule.time.minute,
                json.dumps(list(schedule.weekdays)),
                schedule.target.model_dump_json(),
                schedule.action.model_dump_json(),
                schedule.last_triggered_at.isoformat()
                if schedule.last_triggered_at
                else None,
                str(schedule.id),
            ),
        )
        await self._conn.commit()
        return schedule

    async def delete_schedule(self, schedule_id: UUID) -> bool:
        """Delete a schedule"""
        cursor = await self._conn.execute(
            "DELETE FROM schedules WHERE id = ?", (str(schedule_id),)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get_enabled_schedules(self) -> list[ScheduleConfig]:
        """Get all enabled schedules"""
        cursor = await self._conn.execute(
            "SELECT * FROM schedules WHERE is_enabled = 1 ORDER BY hour, minute"
        )
        rows = await cursor.fetchall()
        return [self._row_to_schedule(row) for row in rows]

    def _row_to_schedule(self, row: aiosqlite.Row) -> ScheduleConfig:
        """Convert database row to ScheduleConfig"""
        return ScheduleConfig(
            id=UUID(row["id"]),
            name=row["name"],
            is_enabled=bool(row["is_enabled"]),
            time=ScheduleTime(hour=row["hour"], minute=row["minute"]),
            weekdays=set(json.loads(row["weekdays"])),
            target=TimerTarget.model_validate_json(row["target_json"]),
            action=TimerAction.model_validate_json(row["action_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_triggered_at=datetime.fromisoformat(row["last_triggered_at"])
            if row["last_triggered_at"]
            else None,
        )

    # Preset Operations

    async def get_presets(self) -> list[PresetConfig]:
        """Get all presets"""
        cursor = await self._conn.execute("SELECT * FROM presets ORDER BY name")
        rows = await cursor.fetchall()
        return [self._row_to_preset(row) for row in rows]

    async def get_preset(self, preset_id: UUID) -> Optional[PresetConfig]:
        """Get a preset by ID"""
        cursor = await self._conn.execute(
            "SELECT * FROM presets WHERE id = ?", (str(preset_id),)
        )
        row = await cursor.fetchone()
        return self._row_to_preset(row) if row else None

    async def create_preset(self, preset: PresetConfig) -> PresetConfig:
        """Create a new preset"""
        await self._conn.execute(
            """
            INSERT INTO presets (id, name, icon, color, snapshots_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(preset.id),
                preset.name,
                preset.icon,
                preset.color,
                json.dumps([s.model_dump() for s in preset.snapshots]),
                preset.created_at.isoformat(),
                preset.updated_at.isoformat(),
            ),
        )
        await self._conn.commit()
        return preset

    async def update_preset(self, preset: PresetConfig) -> PresetConfig:
        """Update an existing preset"""
        preset.updated_at = datetime.now()
        await self._conn.execute(
            """
            UPDATE presets SET
                name = ?, icon = ?, color = ?, snapshots_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                preset.name,
                preset.icon,
                preset.color,
                json.dumps([s.model_dump() for s in preset.snapshots]),
                preset.updated_at.isoformat(),
                str(preset.id),
            ),
        )
        await self._conn.commit()
        return preset

    async def delete_preset(self, preset_id: UUID) -> bool:
        """Delete a preset"""
        cursor = await self._conn.execute(
            "DELETE FROM presets WHERE id = ?", (str(preset_id),)
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_preset(self, row: aiosqlite.Row) -> PresetConfig:
        """Convert database row to PresetConfig"""
        snapshots_data = json.loads(row["snapshots_json"])
        return PresetConfig(
            id=UUID(row["id"]),
            name=row["name"],
            icon=row["icon"],
            color=row["color"],
            snapshots=[ZoneSnapshot.model_validate(s) for s in snapshots_data],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


# Global database instance
_db: Optional[Database] = None


async def get_db() -> Database:
    """Get the database instance"""
    global _db
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db


async def init_db(db_path: Path) -> Database:
    """Initialize the database"""
    global _db
    _db = Database(db_path)
    await _db.connect()
    return _db


async def close_db():
    """Close the database"""
    global _db
    if _db:
        await _db.close()
        _db = None
