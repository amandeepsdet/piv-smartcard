"""Hex / X.509 helpers and card identification (port of ``util.ts``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding


def to_hex(data: Sequence[int], sep: str = "") -> str:
    """Render a byte sequence as an uppercase hex string."""
    return sep.join(f"{b & 0xFF:02X}" for b in data)


def from_hex(text: str) -> List[int]:
    """Parse a hex string (spaces/colons allowed) into a list of ints."""
    cleaned = "".join(c for c in text if c not in " :\t\r\n")
    if len(cleaned) % 2 != 0:
        raise ValueError("hex string must have an even number of digits")
    return [int(cleaned[i : i + 2], 16) for i in range(0, len(cleaned), 2)]


@dataclass
class CertificateInfo:
    """Human-readable summary of an X.509 certificate."""

    subject: str
    issuer: str
    serial_number: str
    not_before: str
    not_after: str
    fingerprint_sha256: str
    pem: str

    def as_lines(self) -> str:
        return (
            f"Subject:      {self.subject}\n"
            f"Issuer:       {self.issuer}\n"
            f"Serial:       {self.serial_number}\n"
            f"Valid from:   {self.not_before}\n"
            f"Valid until:  {self.not_after}\n"
            f"SHA-256:      {self.fingerprint_sha256}"
        )


def parse_certificate(der: Sequence[int]) -> CertificateInfo:
    """Parse DER-encoded certificate bytes into a CertificateInfo."""
    cert = x509.load_der_x509_certificate(bytes(der))
    fingerprint = to_hex(cert.fingerprint(hashes.SHA256()), sep=":")
    return CertificateInfo(
        subject=cert.subject.rfc4514_string(),
        issuer=cert.issuer.rfc4514_string(),
        serial_number=format(cert.serial_number, "X"),
        not_before=cert.not_valid_before_utc.isoformat(),
        not_after=cert.not_valid_after_utc.isoformat(),
        fingerprint_sha256=fingerprint,
        pem=cert.public_bytes(Encoding.PEM).decode("ascii"),
    )


def identify_card(atr: Sequence[int]) -> str:
    """Best-effort friendly name for a card, derived from its ATR.

    The ATR (Answer To Reset) is a short byte string every card emits on
    power-up. We match a few well-known prefixes; unknown cards just get
    their raw ATR echoed back.
    """
    atr_hex = to_hex(atr)
    known = {
        "3BFC13": "Gemalto / PIV",
        "3B7D": "YubiKey PIV",
        "3BF81300008131FE": "YubiKey 5 (PIV)",
        "3BDB96": "PIVKey",
    }
    for prefix, name in known.items():
        if atr_hex.startswith(prefix):
            return name
    return f"Unknown card (ATR {atr_hex})"
