"""PIV applet operations (port of ``piv.ts``).

Implements just enough of NIST SP 800-73-4 to select the PIV
application and read an X.509 certificate object off the card, matching
what the web demo does with the Card Authentication certificate.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Sequence

from . import ber
from .apdu import CommandAPDU, SW1_MORE_DATA, SW_SUCCESS
from .util import CertificateInfo, parse_certificate

if TYPE_CHECKING:  # avoid importing pyscard (reader) at runtime for testability
    from .reader import CardSession

# Application identifier of the PIV Card Application (SP 800-73-4, part 1).
PIV_AID = [0xA0, 0x00, 0x00, 0x03, 0x08, 0x00, 0x00, 0x10, 0x00, 0x01, 0x00]

# Instruction bytes.
INS_SELECT = 0xA4
INS_GET_DATA = 0xCB
INS_GET_RESPONSE = 0xC0


@dataclass(frozen=True)
class CertificateSlot:
    """A named PIV certificate object with its BER object identifier."""

    name: str
    key_reference: int
    object_id: List[int]


# The four X.509 certificate objects defined by PIV, keyed by slot.
SLOTS = {
    "authentication": CertificateSlot("PIV Authentication", 0x9A, [0x5F, 0xC1, 0x05]),
    "signature": CertificateSlot("Digital Signature", 0x9C, [0x5F, 0xC1, 0x0A]),
    "key_management": CertificateSlot("Key Management", 0x9D, [0x5F, 0xC1, 0x0B]),
    "card_authentication": CertificateSlot("Card Authentication", 0x9E, [0x5F, 0xC1, 0x01]),
}

# Tags inside a PIV certificate data object (SP 800-73-4, part 1, table 18).
TAG_DATA_OBJECT = 0x53
TAG_CERTIFICATE = 0x70
TAG_CERT_INFO = 0x71


class PivError(Exception):
    """Raised for PIV-level failures (select / read)."""


def select(session: "CardSession") -> List[int]:
    """SELECT the PIV application; return the raw application property TLV."""
    command = CommandAPDU(cla=0x00, ins=INS_SELECT, p1=0x04, p2=0x00, data=PIV_AID, le=0x00)
    response = session.transmit(command)
    response.raise_for_status("SELECT PIV application failed")
    return response.data


def _get_data(session: "CardSession", object_id: Sequence[int]) -> List[int]:
    """Issue GET DATA for a BER object id, following GET RESPONSE chaining.

    A PIV certificate is usually larger than a single 256-byte APDU, so
    the card answers with SW=61xx and we keep issuing GET RESPONSE until
    it returns 9000.
    """
    # Wrap the object id in tag 0x5C as required by GET DATA.
    tag_list = [0x5C, len(object_id), *object_id]
    command = CommandAPDU(cla=0x00, ins=INS_GET_DATA, p1=0x3F, p2=0xFF, data=tag_list, le=0x00)
    response = session.transmit(command)

    data: List[int] = list(response.data)
    while response.sw1 == SW1_MORE_DATA:
        remaining = response.sw2  # 0x00 means "up to 256 bytes".
        get_response = CommandAPDU(cla=0x00, ins=INS_GET_RESPONSE, p1=0x00, p2=0x00, le=remaining)
        response = session.transmit(get_response)
        data.extend(response.data)

    if response.sw != SW_SUCCESS:
        response.raise_for_status("GET DATA failed")
    return data


def read_certificate_der(
    session: "CardSession", slot: str = "card_authentication"
) -> List[int]:
    """Read and return the DER bytes of the certificate in ``slot``."""
    if slot not in SLOTS:
        raise PivError(f"Unknown slot: {slot!r}. Valid: {', '.join(SLOTS)}")

    raw = _get_data(session, SLOTS[slot].object_id)

    container = ber.find(raw, TAG_DATA_OBJECT)
    source = container.value if container is not None else raw

    cert_tlv = ber.find(source, TAG_CERTIFICATE)
    if cert_tlv is None:
        raise PivError(f"No certificate found in slot {slot!r}")
    cert_bytes = cert_tlv.value

    # CertInfo bit 0 set => the certificate is gzip-compressed.
    info_tlv = ber.find(source, TAG_CERT_INFO)
    if info_tlv is not None and info_tlv.value and (info_tlv.value[0] & 0x01):
        cert_bytes = list(gzip.decompress(bytes(cert_bytes)))

    return cert_bytes


def read_certificate(
    session: "CardSession", slot: str = "card_authentication"
) -> CertificateInfo:
    """High-level: read a slot and return a parsed CertificateInfo."""
    der = read_certificate_der(session, slot)
    return parse_certificate(der)
