"""PIV read logic tests using a fake in-memory card session.

No hardware or PC/SC stack is needed: a fake session returns canned
APDU responses so we can exercise SELECT + GET DATA + BER extraction.
"""

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID

from smartcard_demo import piv
from smartcard_demo.apdu import CommandAPDU, ResponseAPDU


def _der_cert() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Fake Card Auth")])
    now = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(0xABCD)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
        .public_bytes(Encoding.DER)
    )


def _ber_len(n: int) -> list[int]:
    if n < 0x80:
        return [n]
    body = []
    while n:
        body.insert(0, n & 0xFF)
        n >>= 8
    return [0x80 | len(body), *body]


def _wrap_certificate(der: bytes) -> list[int]:
    cert_tlv = [0x70, *_ber_len(len(der)), *der]
    info_tlv = [0x71, 0x01, 0x00]  # CertInfo: uncompressed
    inner = cert_tlv + info_tlv
    return [0x53, *_ber_len(len(inner)), *inner]


class FakeSession:
    def __init__(self, get_data_payload: list[int]) -> None:
        self._payload = get_data_payload

    def get_atr(self):
        return [0x3B, 0x7D]

    def transmit(self, command: CommandAPDU) -> ResponseAPDU:
        if command.ins == piv.INS_SELECT:
            return ResponseAPDU(data=[0x61, 0x11], sw1=0x90, sw2=0x00)
        if command.ins == piv.INS_GET_DATA:
            return ResponseAPDU(data=list(self._payload), sw1=0x90, sw2=0x00)
        raise AssertionError(f"unexpected INS 0x{command.ins:02X}")


def test_select_ok():
    session = FakeSession([])
    assert piv.select(session) == [0x61, 0x11]


def test_read_certificate_uncompressed():
    der = _der_cert()
    session = FakeSession(_wrap_certificate(der))
    info = piv.read_certificate(session, "card_authentication")
    assert "Fake Card Auth" in info.subject
    assert info.serial_number == "ABCD"


def test_unknown_slot_raises():
    session = FakeSession([])
    try:
        piv.read_certificate_der(session, "does_not_exist")
        assert False, "expected PivError"
    except piv.PivError:
        pass
