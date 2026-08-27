"""PC/SC reader connection layer.

In the original demo the browser's Web Smart Card API provided
``navigator.smartCard`` to connect to readers. That API only exists on
ChromeOS, so here we use the native PC/SC stack via ``pyscard`` which is
available on Windows, macOS and Linux.

This module intentionally hides ``pyscard`` behind a small interface so
the rest of the app never imports it directly.
"""

from __future__ import annotations

from typing import List, Sequence

from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.Exceptions import CardConnectionException, NoCardException

from .apdu import CommandAPDU, ResponseAPDU


class ReaderError(Exception):
    """Raised for reader discovery / connection problems."""


def list_readers() -> List[str]:
    """Return the names of all connected PC/SC readers."""
    try:
        return [str(r) for r in readers()]
    except Exception as exc:  # pragma: no cover - depends on host PC/SC
        raise ReaderError(f"Unable to enumerate readers: {exc}") from exc


class CardSession:
    """An open connection to a single card in a single reader.

    Mirrors the connect / transmit / disconnect lifecycle of the web
    demo's ``SmartCardConnection``.
    """

    def __init__(self, reader_name: str) -> None:
        self.reader_name = reader_name
        self._connection: CardConnection | None = None

    # -- lifecycle ---------------------------------------------------------
    def connect(self) -> "CardSession":
        target = None
        for reader in readers():
            if str(reader) == self.reader_name:
                target = reader
                break
        if target is None:
            raise ReaderError(f"Reader not found: {self.reader_name}")
        try:
            self._connection = target.createConnection()
            # T=0 / T=1 negotiated automatically.
            self._connection.connect()
        except NoCardException as exc:
            raise ReaderError("No card present in the reader") from exc
        except CardConnectionException as exc:
            raise ReaderError(f"Failed to connect: {exc}") from exc
        return self

    def disconnect(self) -> None:
        if self._connection is not None:
            try:
                self._connection.disconnect()
            finally:
                self._connection = None

    @property
    def connected(self) -> bool:
        return self._connection is not None

    # -- data --------------------------------------------------------------
    def get_atr(self) -> List[int]:
        """Return the card's Answer-To-Reset bytes."""
        self._require_connection()
        return list(self._connection.getATR())

    def transmit(self, command: CommandAPDU) -> ResponseAPDU:
        """Send one command APDU and return the parsed response."""
        self._require_connection()
        raw = command.serialize()
        data, sw1, sw2 = self._connection.transmit(raw)
        return ResponseAPDU(data=list(data), sw1=sw1, sw2=sw2)

    # -- context manager ---------------------------------------------------
    def __enter__(self) -> "CardSession":
        return self.connect()

    def __exit__(self, *exc_info) -> None:
        self.disconnect()

    def _require_connection(self) -> None:
        if self._connection is None:
            raise ReaderError("Not connected. Call connect() first.")
