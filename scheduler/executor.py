"""
Schedule execution logic using APScheduler
"""
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from models.schedule import ScheduleConfig
from models.action import TimerActionType, TargetType
from protocol import iTachConnection
from db.database import Database

logger = logging.getLogger(__name__)


class ScheduleExecutor:
    """
    Manages scheduled job execution using APScheduler.

    Loads schedules from the database and creates corresponding
    APScheduler jobs. Handles schedule execution when triggered.
    """

    def __init__(self, connection: iTachConnection, db: Database):
        self.connection = connection
        self.db = db
        self.scheduler = AsyncIOScheduler()

    async def start(self):
        """Start the scheduler and load all enabled schedules"""
        logger.info("Starting schedule executor")
        self.scheduler.start()
        await self.reload_schedules()

    async def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping schedule executor")
        self.scheduler.shutdown(wait=False)

    async def reload_schedules(self):
        """Reload all schedules from database"""
        logger.info("Reloading schedules from database")

        # Remove all existing jobs
        self.scheduler.remove_all_jobs()

        # Load enabled schedules
        schedules = await self.db.get_enabled_schedules()
        logger.info(f"Found {len(schedules)} enabled schedules")

        for schedule in schedules:
            self._add_schedule_job(schedule)

    def _add_schedule_job(self, schedule: ScheduleConfig):
        """Add a schedule to APScheduler"""
        # Convert weekdays (1=Sunday...7=Saturday) to cron format (0=Monday...6=Sunday)
        # iOS: 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri, 7=Sat
        # Cron: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        cron_day_map = {
            1: 6,  # Sunday
            2: 0,  # Monday
            3: 1,  # Tuesday
            4: 2,  # Wednesday
            5: 3,  # Thursday
            6: 4,  # Friday
            7: 5,  # Saturday
        }

        cron_days = ",".join(str(cron_day_map[d]) for d in sorted(schedule.weekdays))

        trigger = CronTrigger(
            hour=schedule.time.hour,
            minute=schedule.time.minute,
            day_of_week=cron_days,
        )

        self.scheduler.add_job(
            self._execute_schedule,
            trigger=trigger,
            id=str(schedule.id),
            args=[schedule],
            replace_existing=True,
            name=schedule.name,
        )

        logger.info(
            f"Added schedule job: {schedule.name} at {schedule.time.hour:02d}:{schedule.time.minute:02d} "
            f"on days {cron_days}"
        )

    async def _execute_schedule(self, schedule: ScheduleConfig):
        """Execute a scheduled action"""
        logger.info(f"Executing schedule: {schedule.name}")

        try:
            # Get target zones
            zones = await self._resolve_target_zones(schedule)
            logger.info(f"Target zones: {zones}")

            # Execute action
            await self._execute_action(schedule, zones)

            # Update last triggered time
            schedule.last_triggered_at = datetime.now()
            await self.db.update_schedule(schedule)

            logger.info(f"Schedule '{schedule.name}' executed successfully")

        except Exception as e:
            logger.error(f"Failed to execute schedule '{schedule.name}': {e}")

    async def _resolve_target_zones(self, schedule: ScheduleConfig) -> set[int]:
        """Resolve target zones from schedule configuration"""
        from uuid import UUID

        target = schedule.target

        if target.type == TargetType.ALL_ZONES:
            return {1, 2, 3, 4, 5, 6}
        elif target.type == TargetType.SPECIFIC_ZONES:
            return target.zone_ids or set()
        elif target.type == TargetType.PRESET:
            # Load preset and get its zones
            if target.preset_id:
                preset_uuid = target.preset_id if isinstance(target.preset_id, UUID) else UUID(str(target.preset_id))
                preset = await self.db.get_preset(preset_uuid)
                if preset:
                    return {snapshot.zone_id for snapshot in preset.snapshots}
                else:
                    logger.warning(f"Preset {target.preset_id} not found for target resolution")
            return set()

        return set()

    async def _execute_action(self, schedule: ScheduleConfig, zones: set[int]):
        """Execute the schedule's action on the target zones"""
        action = schedule.action

        match action.type:
            case TimerActionType.POWER_OFF:
                for zone in zones:
                    await self.connection.set_power(zone, False)
                    logger.debug(f"Zone {zone} powered off")

            case TimerActionType.POWER_ON:
                for zone in zones:
                    await self.connection.set_power(zone, True)
                    logger.debug(f"Zone {zone} powered on")

            case TimerActionType.SET_SOURCE:
                if action.source_id:
                    for zone in zones:
                        await self.connection.set_source(zone, action.source_id)
                        logger.debug(f"Zone {zone} source set to {action.source_id}")

            case TimerActionType.SET_VOLUME:
                if action.volume is not None:
                    for zone in zones:
                        await self.connection.set_volume(zone, action.volume)
                        logger.debug(f"Zone {zone} volume set to {action.volume}")

            case TimerActionType.APPLY_PRESET:
                if action.preset_id:
                    await self._apply_preset(action.preset_id)

    async def _apply_preset(self, preset_id):
        """Apply a preset"""
        from uuid import UUID

        preset = await self.db.get_preset(
            preset_id if isinstance(preset_id, UUID) else UUID(str(preset_id))
        )
        if not preset:
            logger.warning(f"Preset {preset_id} not found")
            return

        logger.info(f"Applying preset: {preset.name}")

        for snapshot in preset.snapshots:
            zone_id = snapshot.zone_id

            # Set power first
            await self.connection.set_power(zone_id, snapshot.power)

            if snapshot.power:
                await self.connection.set_source(zone_id, snapshot.source)
                await self.connection.set_volume(zone_id, snapshot.volume)
                await self.connection.set_mute(zone_id, snapshot.mute)
                await self.connection.set_bass(zone_id, snapshot.bass)
                await self.connection.set_treble(zone_id, snapshot.treble)
                await self.connection.set_balance(zone_id, snapshot.balance)


# Module-level executor instance for use by API
_executor: Optional[ScheduleExecutor] = None


def get_executor() -> Optional[ScheduleExecutor]:
    """Get the global executor instance"""
    return _executor


def set_executor(executor: ScheduleExecutor):
    """Set the global executor instance"""
    global _executor
    _executor = executor


async def execute_schedule(schedule: ScheduleConfig):
    """Execute a schedule immediately (for API use)"""
    if _executor:
        await _executor._execute_schedule(schedule)
    else:
        raise RuntimeError("Schedule executor not initialized")
