from smartcard_demo.apdu import (
    ApduError,
    CommandAPDU,
    ResponseAPDU,
    SW_SUCCESS,
)


def test_command_serialize_no_data():
    cmd = CommandAPDU(cla=0x00, ins=0xA4, p1=0x04, p2=0x00)
    assert cmd.serialize() == [0x00, 0xA4, 0x04, 0x00]


def test_command_serialize_with_data_and_le():
    cmd = CommandAPDU(cla=0x00, ins=0xA4, p1=0x04, p2=0x00, data=[0xA0, 0x00], le=0x00)
    assert cmd.serialize() == [0x00, 0xA4, 0x04, 0x00, 0x02, 0xA0, 0x00, 0x00]


def test_response_deserialize():
    resp = ResponseAPDU.deserialize([0xDE, 0xAD, 0x90, 0x00])
    assert resp.data == [0xDE, 0xAD]
    assert resp.sw == SW_SUCCESS
    assert resp.is_success


def test_response_short_raises():
    try:
        ResponseAPDU.deserialize([0x90])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_raise_for_status():
    resp = ResponseAPDU(data=[], sw1=0x6A, sw2=0x82)
    try:
        resp.raise_for_status("select")
        assert False, "expected ApduError"
    except ApduError as exc:
        assert exc.sw == 0x6A82
