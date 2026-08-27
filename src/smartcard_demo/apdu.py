"""APDU command / response serialization (port of ``apdu.ts``).

An APDU (Application Protocol Data Unit) is the packet format used to
talk to a smart card, as defined by ISO/IEC 7816-4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

# Status word (SW1 SW2) returned by the card when everything is fine.
SW_SUCCESS = 0x9000
# The card has more bytes available; SW2 tells how many to fetch next.
SW1_MORE_DATA = 0x61
# Wrong Le field; SW2 tells the correct length to ask for.
SW1_WRONG_LE = 0x6C


class ApduError(Exception):
    """Raised when a card returns a non-success status word."""

    def __init__(self, sw: int, message: str = "") -> None:
        self.sw = sw
        detail = f"0x{sw:04X}"
        super().__init__(f"{message} (SW={detail})" if message else f"APDU failed (SW={detail})")


@dataclass
class CommandAPDU:
    """A command APDU sent to the card.

    Serializes to the ISO 7816-4 short form:
        CLA INS P1 P2 [Lc DATA] [Le]
    """

    cla: int
    ins: int
    p1: int
    p2: int
    data: Sequence[int] = field(default_factory=list)
    le: int | None = None

    def serialize(self) -> List[int]:
        out: List[int] = [self.cla & 0xFF, self.ins & 0xFF, self.p1 & 0xFF, self.p2 & 0xFF]
        data = list(self.data)
        if data:
            if len(data) > 0xFF:
                raise ValueError("short-form APDU cannot carry more than 255 data bytes")
            out.append(len(data))
            out.extend(b & 0xFF for b in data)
        if self.le is not None:
            out.append(self.le & 0xFF)
        return out


@dataclass
class ResponseAPDU:
    """A response APDU received from the card: DATA followed by SW1 SW2."""

    data: List[int]
    sw1: int
    sw2: int

    @property
    def sw(self) -> int:
        """The combined 16-bit status word."""
        return (self.sw1 << 8) | self.sw2

    @property
    def is_success(self) -> bool:
        return self.sw == SW_SUCCESS

    @classmethod
    def deserialize(cls, raw: Sequence[int]) -> "ResponseAPDU":
        """Split a raw card response into data + status word.

        The final two bytes are always SW1/SW2; everything before is data.
        """
        raw = list(raw)
        if len(raw) < 2:
            raise ValueError("response APDU too short to contain a status word")
        return cls(data=raw[:-2], sw1=raw[-2], sw2=raw[-1])

    def raise_for_status(self, message: str = "") -> "ResponseAPDU":
        if not self.is_success:
            raise ApduError(self.sw, message)
        return self
