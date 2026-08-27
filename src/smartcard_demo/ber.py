"""Minimal BER-TLV decoder (port of ``ber.ts``).

PIV data objects are encoded as BER-TLV (ISO/IEC 8825-1). We only need
enough of the format to walk the tag/length/value tree returned by a
PIV card, so this is intentionally small.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

# PIV wraps nested TLVs inside these tags even though the ISO "constructed"
# bit (0x20) is not set on them, so treat them as constructed when walking.
TEMPLATE_TAGS = frozenset({0x53, 0x7E})


@dataclass
class TLV:
    """A single Tag-Length-Value element."""

    tag: int
    value: List[int]

    def is_constructed(self) -> bool:
        """True if the value itself contains more TLV elements.

        Bit 6 (0x20) of the first tag byte marks a constructed element;
        a few PIV template tags nest TLVs without setting that bit.
        """
        if self.tag in TEMPLATE_TAGS:
            return True
        first_byte = self.tag
        while first_byte > 0xFF:
            first_byte >>= 8
        return bool(first_byte & 0x20)

    def children(self) -> List["TLV"]:
        if not self.is_constructed():
            return []
        # A "constructed" tag may still hold opaque bytes (e.g. PIV stores
        # raw certificate DER under tag 0x70); parse defensively.
        try:
            return parse(self.value)
        except (IndexError, ValueError):
            return []

    def find(self, tag: int) -> "TLV | None":
        """Depth-first search for the first descendant with ``tag``."""
        for child in self.children():
            if child.tag == tag:
                return child
            found = child.find(tag)
            if found is not None:
                return found
        return None


def _read_tag(data: Sequence[int], offset: int) -> Tuple[int, int]:
    """Return (tag, new_offset). Supports multi-byte tags."""
    tag = data[offset]
    offset += 1
    # Low 5 bits all set => tag continues in following bytes.
    if (tag & 0x1F) == 0x1F:
        while True:
            tag = (tag << 8) | data[offset]
            more = data[offset] & 0x80
            offset += 1
            if not more:
                break
    return tag, offset


def _read_length(data: Sequence[int], offset: int) -> Tuple[int, int]:
    """Return (length, new_offset). Supports the multi-byte long form."""
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    num_bytes = first & 0x7F
    length = 0
    for _ in range(num_bytes):
        length = (length << 8) | data[offset]
        offset += 1
    return length, offset


def parse(data: Sequence[int]) -> List[TLV]:
    """Parse a byte sequence into a flat list of top-level TLV elements."""
    data = list(data)
    result: List[TLV] = []
    offset = 0
    while offset < len(data):
        tag, offset = _read_tag(data, offset)
        length, offset = _read_length(data, offset)
        value = data[offset : offset + length]
        offset += length
        result.append(TLV(tag=tag, value=value))
    return result


def find(data: Sequence[int], tag: int) -> TLV | None:
    """Find the first TLV with ``tag`` anywhere in the tree."""
    for tlv in parse(data):
        if tlv.tag == tag:
            return tlv
        found = tlv.find(tag)
        if found is not None:
            return found
    return None
