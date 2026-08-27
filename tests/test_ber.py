from smartcard_demo import ber


def test_parse_simple():
    # Tag 0x70, length 3, value DE AD BE
    tlvs = ber.parse([0x70, 0x03, 0xDE, 0xAD, 0xBE])
    assert len(tlvs) == 1
    assert tlvs[0].tag == 0x70
    assert tlvs[0].value == [0xDE, 0xAD, 0xBE]


def test_long_form_length():
    value = list(range(200))
    encoded = [0x70, 0x81, 200, *value]
    tlvs = ber.parse(encoded)
    assert tlvs[0].value == value


def test_constructed_and_find():
    # 0x53 (constructed) { 0x70 len2 [AA BB], 0x71 len1 [00] }
    inner = [0x70, 0x02, 0xAA, 0xBB, 0x71, 0x01, 0x00]
    encoded = [0x53, len(inner), *inner]
    cert = ber.find(encoded, 0x70)
    assert cert is not None
    assert cert.value == [0xAA, 0xBB]
    info = ber.find(encoded, 0x71)
    assert info is not None and info.value == [0x00]


def test_multibyte_tag():
    # Tag 0x5F 0xC1 0x05 style (first byte low bits set => continues)
    tlvs = ber.parse([0x5F, 0xC1, 0x05, 0x00])
    assert tlvs[0].tag == 0x5FC105
    assert tlvs[0].value == []
