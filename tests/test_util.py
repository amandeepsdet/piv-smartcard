import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID

from smartcard_demo import util


def _make_der_cert() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test PIV Card")])
    now = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(0x1234)
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(Encoding.DER)


def test_hex_roundtrip():
    assert util.to_hex([0xDE, 0xAD, 0xBE]) == "DEADBE"
    assert util.from_hex("DE:AD BE") == [0xDE, 0xAD, 0xBE]


def test_parse_certificate():
    der = _make_der_cert()
    info = util.parse_certificate(list(der))
    assert "Test PIV Card" in info.subject
    assert info.serial_number == "1234"
    assert info.pem.startswith("-----BEGIN CERTIFICATE-----")
    assert len(info.fingerprint_sha256.split(":")) == 32


def test_identify_card_known_and_unknown():
    assert util.identify_card(util.from_hex("3B7D000000")) == "YubiKey PIV"
    assert util.identify_card([0x00, 0x11]).startswith("Unknown card")
