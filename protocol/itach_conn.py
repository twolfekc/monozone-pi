"""
iTach TCP Connection Manager

Handles TCP connection to iTach Flex (IP-to-RS232 bridge).
Uses the same protocol as the iOS app.
"""
import asyncio
import logging
from typing import Optional, Callable
from dataclasses import dataclass

from .commands import CommandBuilder
from .parser import ResponseParser, ZoneState

logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    """Current connection state"""

    connected: bool = False
    host: str = ""
    port: int = 0
    last_error: Optional[str] = None


class iTachConnection:
    """
    Async TCP connection to iTach Flex.

    Provides methods for sending commands and receiving responses.
    Handles reconnection automatically.
    """

    def __init__(
        self,
        host: str,
        port: int = 4999,
        timeout: float = 2.0,
        reconnect_delay: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._last_error: Optional[str] = None

        # Zone state cache
        self._zone_states: dict[int, ZoneState] = {}

        # Callbacks
        self._on_state_change: Optional[Callable[[int, ZoneState], None]] = None
        self._on_connection_change: Optional[Callable[[bool], None]] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def state(self) -> ConnectionState:
        return ConnectionState(
            connected=self._connected,
            host=self.host,
            port=self.port,
            last_error=self._last_error,
        )

    @property
    def zone_states(self) -> dict[int, ZoneState]:
        return self._zone_states.copy()

    def on_state_change(self, callback: Callable[[int, ZoneState], None]):
        """Register callback for zone state changes"""
        self._on_state_change = callback

    def on_connection_change(self, callback: Callable[[bool], None]):
        """Register callback for connection state changes"""
        self._on_connection_change = callback

    async def connect(self) -> bool:
        """
        Establish TCP connection to iTach.

        Returns:
            True if connected successfully
        """
        async with self._lock:
            if self._connected:
                return True

            try:
                logger.info(f"Connecting to iTach at {self.host}:{self.port}")

                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout,
                )

                self._connected = True
                self._last_error = None
                logger.info("Connected to iTach")

                if self._on_connection_change:
                    self._on_connection_change(True)

                return True

            except asyncio.TimeoutError:
                self._last_error = "Connection timeout"
                logger.warning(f"Connection timeout to {self.host}:{self.port}")
            except ConnectionRefusedError:
                self._last_error = "Connection refused"
                logger.warning(f"Connection refused by {self.host}:{self.port}")
            except OSError as e:
                self._last_error = str(e)
                logger.warning(f"Connection error: {e}")

            self._connected = False
            return False

    async def disconnect(self):
        """Close the TCP connection"""
        async with self._lock:
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception as e:
                    logger.debug(f"Error closing connection: {e}")

            self._reader = None
            self._writer = None
            self._connected = False

            if self._on_connection_change:
                self._on_connection_change(False)

            logger.info("Disconnected from iTach")

    async def _send_receive(self, command: bytes) -> Optional[bytes]:
        """
        Send command and receive response.

        Args:
            command: Raw command bytes

        Returns:
            Response bytes or None on error
        """
        if not self._connected:
            if not await self.connect():
                return None

        try:
            async with self._lock:
                if not self._writer or not self._reader:
                    return None

                # Send command
                self._writer.write(command)
                await self._writer.drain()

                # Read response - iTach sends echo (#?ZZ) then status (#>ZZ...)
                # Accumulate data until we find a line with >
                data = b""
                deadline = asyncio.get_event_loop().time() + self.timeout

                while asyncio.get_event_loop().time() < deadline:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break

                    try:
                        chunk = await asyncio.wait_for(
                            self._reader.read(256), timeout=remaining
                        )
                        if chunk:
                            data += chunk
                            # Check if we have a status response
                            for line in data.split(b"\r"):
                                if b">" in line:
                                    return line + b"\r"
                    except asyncio.TimeoutError:
                        break

                # Final check of accumulated data
                for line in data.split(b"\r"):
                    if b">" in line:
                        return line + b"\r"

                raise asyncio.TimeoutError()

        except asyncio.TimeoutError:
            logger.warning("Response timeout")
            self._last_error = "Response timeout"
            await self._handle_disconnect()
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.warning(f"Connection lost: {e}")
            self._last_error = str(e)
            await self._handle_disconnect()
        except Exception as e:
            logger.error(f"Send/receive error: {e}")
            self._last_error = str(e)
            await self._handle_disconnect()

        return None

    async def _handle_disconnect(self):
        """Handle unexpected disconnection"""
        self._connected = False
        self._reader = None
        self._writer = None

        if self._on_connection_change:
            self._on_connection_change(False)

    # Zone Query Methods

    async def query_zone(self, zone: int) -> Optional[ZoneState]:
        """
        Query a single zone's state.

        Args:
            zone: Zone number (1-6)

        Returns:
            ZoneState or None on error
        """
        command = CommandBuilder.query(zone)
        response = await self._send_receive(command)

        if response:
            state = ResponseParser.parse_response(response)
            if state:
                self._zone_states[zone] = state
                if self._on_state_change:
                    self._on_state_change(zone, state)
                return state

        return None

    async def query_all_zones(self) -> dict[int, ZoneState]:
        """
        Query all 6 zones.

        Returns:
            Dictionary of zone number to ZoneState
        """
        results = {}
        for zone in range(1, 7):
            state = await self.query_zone(zone)
            if state:
                results[zone] = state
            # Small delay between queries to avoid overwhelming iTach
            await asyncio.sleep(0.05)

        return results

    # Zone Control Methods

    async def set_power(self, zone: int, on: bool) -> bool:
        """Set zone power on/off"""
        command = CommandBuilder.set_power(zone, on)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)  # Update cached state
            return True
        return False

    async def set_volume(self, zone: int, volume: int) -> bool:
        """Set zone volume (0-38)"""
        command = CommandBuilder.set_volume(zone, volume)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_source(self, zone: int, source: int) -> bool:
        """Set zone source (1-6)"""
        command = CommandBuilder.set_source(zone, source)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_mute(self, zone: int, muted: bool) -> bool:
        """Set zone mute on/off"""
        command = CommandBuilder.set_mute(zone, muted)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_bass(self, zone: int, bass: int) -> bool:
        """Set zone bass (0-14)"""
        command = CommandBuilder.set_bass(zone, bass)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_treble(self, zone: int, treble: int) -> bool:
        """Set zone treble (0-14)"""
        command = CommandBuilder.set_treble(zone, treble)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_balance(self, zone: int, balance: int) -> bool:
        """Set zone balance (0-20)"""
        command = CommandBuilder.set_balance(zone, balance)
        response = await self._send_receive(command)
        if response:
            await self.query_zone(zone)
            return True
        return False

    async def set_all_power(self, on: bool, zones: Optional[list[int]] = None) -> bool:
        """
        Set power for multiple zones.

        Args:
            on: Power state
            zones: List of zone numbers, or None for all zones

        Returns:
            True if all commands succeeded
        """
        if zones is None:
            zones = list(range(1, 7))

        success = True
        for zone in zones:
            if not await self.set_power(zone, on):
                success = False
            await asyncio.sleep(0.05)

        return success
