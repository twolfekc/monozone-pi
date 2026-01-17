"""
RS232 Command Builders for Monoprice 6-Zone Controller

Protocol:
- Set command: <ZZCCVV\r where ZZ=zone(11-16), CC=control code, VV=value
- Query command: ?ZZ\r

Control Codes:
- PR: Power (00/01)
- VO: Volume (00-38)
- CH: Source/Channel (01-06)
- MU: Mute (00/01)
- BS: Bass (00-14, display as -7 to +7)
- TR: Treble (00-14, display as -7 to +7)
- BL: Balance (00-20, display as -10 to +10)
"""


class CommandBuilder:
    """Builds RS232 commands for Monoprice 6-Zone Controller"""

    TERMINATOR = "\r"

    # Control codes
    POWER = "PR"
    VOLUME = "VO"
    SOURCE = "CH"
    MUTE = "MU"
    BASS = "BS"
    TREBLE = "TR"
    BALANCE = "BL"

    @staticmethod
    def _zone_addr(zone: int) -> int:
        """Convert zone number (1-6) to address (11-16)"""
        if not 1 <= zone <= 6:
            raise ValueError(f"Zone must be 1-6, got {zone}")
        return 10 + zone

    @classmethod
    def _build_set(cls, zone: int, code: str, value: int) -> bytes:
        """Build a set command: <ZZCCVV\r"""
        addr = cls._zone_addr(zone)
        cmd = f"<{addr:02d}{code}{value:02d}{cls.TERMINATOR}"
        return cmd.encode("ascii")

    @classmethod
    def query(cls, zone: int) -> bytes:
        """Build a query command: ?ZZ\r"""
        addr = cls._zone_addr(zone)
        cmd = f"?{addr:02d}{cls.TERMINATOR}"
        return cmd.encode("ascii")

    @classmethod
    def query_all(cls) -> list[bytes]:
        """Build query commands for all 6 zones"""
        return [cls.query(z) for z in range(1, 7)]

    @classmethod
    def set_power(cls, zone: int, on: bool) -> bytes:
        """Set zone power on/off"""
        return cls._build_set(zone, cls.POWER, 1 if on else 0)

    @classmethod
    def set_volume(cls, zone: int, volume: int) -> bytes:
        """Set zone volume (0-38)"""
        volume = max(0, min(38, volume))
        return cls._build_set(zone, cls.VOLUME, volume)

    @classmethod
    def set_source(cls, zone: int, source: int) -> bytes:
        """Set zone source/channel (1-6)"""
        source = max(1, min(6, source))
        return cls._build_set(zone, cls.SOURCE, source)

    @classmethod
    def set_mute(cls, zone: int, muted: bool) -> bytes:
        """Set zone mute on/off"""
        return cls._build_set(zone, cls.MUTE, 1 if muted else 0)

    @classmethod
    def set_bass(cls, zone: int, bass: int) -> bytes:
        """Set zone bass (0-14, where 7 = neutral)"""
        bass = max(0, min(14, bass))
        return cls._build_set(zone, cls.BASS, bass)

    @classmethod
    def set_treble(cls, zone: int, treble: int) -> bytes:
        """Set zone treble (0-14, where 7 = neutral)"""
        treble = max(0, min(14, treble))
        return cls._build_set(zone, cls.TREBLE, treble)

    @classmethod
    def set_balance(cls, zone: int, balance: int) -> bytes:
        """Set zone balance (0-20, where 10 = center)"""
        balance = max(0, min(20, balance))
        return cls._build_set(zone, cls.BALANCE, balance)
