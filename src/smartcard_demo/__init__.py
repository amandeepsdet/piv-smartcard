"""Cross-platform PIV smart card library.

A Python port of the GoogleChromeLabs/web-smartcard-demo architecture.
Instead of the ChromeOS-only Web Smart Card API it talks to a real
PC/SC stack (WinSCard on Windows, PCSC framework on macOS, pcscd on
Linux) through the ``pyscard`` library.

Module map (mirrors the original TypeScript project):

    apdu.py   <-  apdu.ts    APDU command / response objects
    ber.py    <-  ber.ts     BER-TLV decoder
    piv.py    <-  piv.ts     PIV applet operations
    util.py   <-  util.ts    hex + X.509 helpers, card identification
    reader.py <-  (browser)  PC/SC reader connect / disconnect
    app.py    <-  index.ts   UI (Tkinter) wiring it all together

The reader symbols (``CardSession``, ``list_readers``, ``ReaderError``) are
imported lazily, so ``import smartcard_demo`` works even when ``pyscard`` is
not installed.
"""

from __future__ import annotations

from .apdu import ApduError, CommandAPDU, ResponseAPDU
from .ber import TLV, find, parse
from .piv import (
    SLOTS,
    CertificateSlot,
    PivError,
    read_certificate,
    read_certificate_der,
    select,
)
from .util import CertificateInfo, from_hex, identify_card, parse_certificate, to_hex

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "CommandAPDU",
    "ResponseAPDU",
    "ApduError",
    "TLV",
    "parse",
    "find",
    "SLOTS",
    "CertificateSlot",
    "PivError",
    "select",
    "read_certificate",
    "read_certificate_der",
    "CertificateInfo",
    "parse_certificate",
    "identify_card",
    "to_hex",
    "from_hex",
    "CardSession",
    "list_readers",
    "ReaderError",
]

# Lazily import the pyscard-backed reader so the pure-Python API is usable
# without pyscard installed (see PEP 562).
_LAZY = {"CardSession", "list_readers", "ReaderError"}


def __getattr__(name: str):
    if name in _LAZY:
        from . import reader

        return getattr(reader, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

