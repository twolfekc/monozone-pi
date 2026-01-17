"""
Response Parser for Monoprice 6-Zone Controller

Response format: >ZZPAPRMUDTVOTRBSBLCHLS\r
- ZZ: Zone address (11-16)
- PA: PA status (00/01)
- PR: Power (00/01)
- MU: Mute (00/01)
- DT: Do Not Disturb (00/01)
- VO: Volume (00-38)
- TR: Treble (00-14)
- BS: Bass (00-14)
- BL: Balance (00-20)
- CH: Source/Channel (01-06)
- LS: Keypad status (00/01)
"""
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ZoneState:
    """Parsed zone state from response"""

    zone: int
    power: bool
    volume: int
    source: int
    mute: bool
    bass: int
    treble: int
    balance: int
    pa: bool = False
    dnd: bool = False
    keypad: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "zone": self.zone,
            "power": self.power,
            "volume": self.volume,
            "source": self.source,
            "mute": self.mute,
            "bass": self.bass,
            "treble": self.treble,
            "balance": self.balance,
            "pa": self.pa,
            "dnd": self.dnd,
            "keypad": self.keypad,
        }


class ResponseParser:
    """Parses RS232 responses from Monoprice 6-Zone Controller"""

    # Response field positions (after >ZZ prefix)
    # Format: >ZZPAPRMUDTVOTRBSBLCHLS
    FIELD_POSITIONS = {
        "pa": (0, 2),
        "power": (2, 4),
        "mute": (4, 6),
        "dnd": (6, 8),
        "volume": (8, 10),
        "treble": (10, 12),
        "bass": (12, 14),
        "balance": (14, 16),
        "source": (16, 18),
        "keypad": (18, 20),
    }

    @classmethod
    def parse_response(cls, response: bytes) -> Optional[ZoneState]:
        """
        Parse a zone query response.

        Args:
            response: Raw bytes from iTach

        Returns:
            ZoneState if valid response, None otherwise
        """
        try:
            # Decode and strip
            text = response.decode("ascii").strip()

            # Must start with >
            if not text.startswith(">"):
                logger.debug(f"Response doesn't start with '>': {text}")
                return None

            # Remove > prefix
            text = text[1:]

            # Need at least zone address (2 chars) + fields (20 chars)
            if len(text) < 22:
                logger.debug(f"Response too short: {text}")
                return None

            # Extract zone address
            zone_addr = int(text[0:2])
            if not 11 <= zone_addr <= 16:
                logger.debug(f"Invalid zone address: {zone_addr}")
                return None

            zone = zone_addr - 10  # Convert back to 1-6

            # Extract fields from remaining text
            fields = text[2:]

            def get_field(name: str) -> int:
                start, end = cls.FIELD_POSITIONS[name]
                return int(fields[start:end])

            return ZoneState(
                zone=zone,
                pa=get_field("pa") == 1,
                power=get_field("power") == 1,
                mute=get_field("mute") == 1,
                dnd=get_field("dnd") == 1,
                volume=get_field("volume"),
                treble=get_field("treble"),
                bass=get_field("bass"),
                balance=get_field("balance"),
                source=get_field("source"),
                keypad=get_field("keypad") == 1,
            )

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse response: {response}, error: {e}")
            return None

    @classmethod
    def parse_multiple(cls, data: bytes) -> list[ZoneState]:
        """
        Parse multiple responses separated by \\r.

        Args:
            data: Raw bytes potentially containing multiple responses

        Returns:
            List of parsed ZoneState objects
        """
        results = []
        responses = data.split(b"\r")

        for response in responses:
            if response:
                state = cls.parse_response(response)
                if state:
                    results.append(state)

        return results
