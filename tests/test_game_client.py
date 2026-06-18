from app.services.game_client import PacketWriter, PacketReader, _cuint_encode, _cuint_decode


def test_cuint_roundtrip():
    for v in [0, 1, 0x7F, 0x80, 0x3FFF, 0x4000, 0x1FFFFFFF, 0x20000000]:
        encoded = _cuint_encode(v)
        decoded, pos = _cuint_decode(encoded, 0)
        assert decoded == v, f"Failed for {v}: got {decoded}"


def test_cuint_1byte():
    assert _cuint_encode(0) == b"\x00"
    assert _cuint_encode(0x7F) == b"\x7F"
    assert len(_cuint_encode(0x7F)) == 1


def test_cuint_2byte():
    encoded = _cuint_encode(0x80)
    assert len(encoded) == 2
    decoded, _ = _cuint_decode(encoded, 0)
    assert decoded == 0x80


def test_cuint_4byte():
    encoded = _cuint_encode(0x4000)
    assert len(encoded) == 4
    decoded, _ = _cuint_decode(encoded, 0)
    assert decoded == 0x4000


def test_packet_writer_ustring():
    pw = PacketWriter()
    pw.write_ustring("hello")
    data = bytes(pw._buf)
    pr = PacketReader(data)
    assert pr.read_ustring() == "hello"


def test_packet_writer_ustring_unicode():
    pw = PacketWriter()
    pw.write_ustring("测试")
    data = bytes(pw._buf)
    pr = PacketReader(data)
    assert pr.read_ustring() == "测试"


def test_packet_writer_octets_bytes():
    pw = PacketWriter()
    pw.write_octets(b"\x01\x02\x03")
    data = bytes(pw._buf)
    pr = PacketReader(data)
    assert pr.read_octets() == "010203"


def test_packet_writer_octets_hex():
    pw = PacketWriter()
    pw.write_octets("deadbeef")
    data = bytes(pw._buf)
    pr = PacketReader(data)
    assert pr.read_octets() == "deadbeef"


def test_packet_frame():
    pw = PacketWriter()
    pw.write_uint32(0xFFFFFFFF)
    pw.write_uint32(12345)
    framed = pw.pack(0xD49)
    pr = PacketReader(framed)
    info = pr.read_packet_info()
    assert info["opcode"] == 0xD49


def test_uint32_roundtrip():
    pw = PacketWriter()
    pw.write_uint32(12345678)
    pr = PacketReader(bytes(pw._buf))
    assert pr.read_uint32() == 12345678


def test_uint32_max():
    pw = PacketWriter()
    pw.write_uint32(0xFFFFFFFF)
    pr = PacketReader(bytes(pw._buf))
    assert pr.read_uint32() == 0xFFFFFFFF


def test_float_roundtrip():
    pw = PacketWriter()
    pw.write_float(3.14)
    pr = PacketReader(bytes(pw._buf))
    v = pr.read_float()
    assert abs(v - 3.14) < 0.001


def test_cls2class():
    from app.services.game_client import GameClient
    client = GameClient()
    assert client._cls2class(2) == 7
    assert client._cls2class(4) == 3
    assert client._cls2class(5) == 8
    assert client._cls2class(6) == 5
    assert client._cls2class(7) == 6
