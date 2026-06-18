"""
Binary packet client for the PW game server's gamedbd socket (port 29400).
Implements the same CUInt/UString/UInt32/Float encoding as the PHP packet_class.php.
"""
import socket
import struct
import logging

GAMEDBD_HOST = "127.0.0.1"
GAMEDBD_PORT = 29400
TIMEOUT = 3

# ── CUInt (variable-length big-endian integer) ───────────────────────────────

def _cuint_decode(data: bytes, pos: int):
    b = data[pos]
    mask = b & 0xE0
    if mask == 0xE0:
        val = struct.unpack_from(">I", data, pos + 1)[0]
        return val, pos + 5
    elif mask == 0xC0:
        val = struct.unpack_from(">I", data, pos)[0] & 0x1FFFFFFF
        return val, pos + 4
    elif mask in (0x80, 0xA0):
        val = struct.unpack_from(">H", data, pos)[0] & 0x3FFF
        return val, pos + 2
    else:
        return b, pos + 1


def _cuint_encode(value: int) -> bytes:
    value = value & 0xFFFFFFFF
    if value <= 0x7F:
        return struct.pack(">B", value)
    elif value <= 0x3FFF:
        return struct.pack(">H", value | 0x8000)
    elif value <= 0x1FFFFFFF:
        return struct.pack(">I", value | 0xC0000000)
    else:
        return b"\xe0" + struct.pack(">I", value)


# ── Primitive readers ─────────────────────────────────────────────────────────

def _read_uint32(data: bytes, pos: int):
    return struct.unpack_from(">I", data, pos)[0], pos + 4


def _read_byte(data: bytes, pos: int):
    return data[pos], pos + 1


def _read_float(data: bytes, pos: int):
    # Wire: big-endian (PHP: strrev(pack("f",...))). Python '>f' reads that correctly.
    return struct.unpack_from(">f", data, pos)[0], pos + 4


def _read_ustring(data: bytes, pos: int):
    length, pos = _cuint_decode(data, pos)
    text = data[pos: pos + length].decode("utf-16-le", errors="replace")
    return text, pos + length


def _read_octets(data: bytes, pos: int):
    length, pos = _cuint_decode(data, pos)
    return data[pos: pos + length], pos + length


# ── Packet builder ────────────────────────────────────────────────────────────

def _build_packet(opcode: int, body: bytes) -> bytes:
    return _cuint_encode(opcode) + _cuint_encode(len(body)) + body


def _write_uint32(value: int) -> bytes:
    return struct.pack(">I", value & 0xFFFFFFFF)


# ── Socket I/O ────────────────────────────────────────────────────────────────

def _send_recv(packet: bytes) -> bytes | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((GAMEDBD_HOST, GAMEDBD_PORT))
            s.sendall(packet)
            buf = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
            return buf
    except Exception:
        return None


def _skip_response_header(data: bytes, pos: int) -> int:
    """Skip: CUInt(opcode) + CUInt(length) + UInt32(always) + UInt32(retcode)."""
    _, pos = _cuint_decode(data, pos)   # opcode
    _, pos = _cuint_decode(data, pos)   # length
    _, pos = _read_uint32(data, pos)    # always
    _, pos = _read_uint32(data, pos)    # retcode
    return pos


# ── cls2class (PHP port) ──────────────────────────────────────────────────────

def _cls2class(cls: int) -> int:
    if 1 < cls < 8 and cls != 3:
        return {2: 7, 4: 3, 5: 8, 6: 5, 7: 6}[cls]
    return cls + 1


# ── Public API ────────────────────────────────────────────────────────────────

def get_user_roles(account_aid: int) -> list[dict]:
    """
    Send opcode 0xD49 to gamedbd — returns list of {role_id, role_name} dicts
    for the given game account ID (point.aid).
    Returns [] if the server is unreachable or the account has no characters.
    """
    body = _write_uint32(0xFFFFFFFF) + _write_uint32(account_aid)
    packet = _build_packet(0xD49, body)
    response = _send_recv(packet)
    if not response:
        return []
    try:
        pos = _skip_response_header(response, 0)
        char_count, pos = _cuint_decode(response, pos)
        roles = []
        for _ in range(char_count):
            role_id, pos = _read_uint32(response, pos)
            role_name, pos = _read_ustring(response, pos)
            roles.append({"role_id": role_id, "role_name": role_name})
        return roles
    except Exception as e:
        logging.warning("get_user_roles parse error: %s", e)
        return []


def get_role_base(role_id: int, classes: dict) -> dict | None:
    """
    Send opcode 0x1F43 to gamedbd — returns character base data dict.
    Returns None if the server is unreachable or parsing fails.
    """
    body = _write_uint32(0xFFFFFFFF) + _write_uint32(role_id)
    packet = _build_packet(0x1F43, body)
    response = _send_recv(packet)
    if not response:
        return None
    try:
        pos = _skip_response_header(response, 0)
        _, pos = _read_byte(response, pos)          # version
        _, pos = _read_uint32(response, pos)        # role_id (echo)
        _, pos = _read_ustring(response, pos)       # name (already have it)
        _, pos = _read_uint32(response, pos)        # race (unused here)
        raw_cls, pos = _read_uint32(response, pos)  # raw class
        _, pos = _read_byte(response, pos)          # gender
        _, pos = _read_octets(response, pos)        # custom_data
        _, pos = _read_octets(response, pos)        # config_data
        _, pos = _read_uint32(response, pos)        # custom_stamp
        _, pos = _read_byte(response, pos)          # status
        _, pos = _read_uint32(response, pos)        # delete_time
        _, pos = _read_uint32(response, pos)        # create_time
        _, pos = _read_uint32(response, pos)        # lastlogin_time
        forbid_count, pos = _cuint_decode(response, pos)
        for _ in range(forbid_count):
            _, pos = _read_byte(response, pos)
            _, pos = _read_uint32(response, pos)
            _, pos = _read_uint32(response, pos)
            _, pos = _read_ustring(response, pos)
        _, pos = _read_octets(response, pos)        # extra octets
        _, pos = _read_uint32(response, pos)
        _, pos = _read_uint32(response, pos)
        _, pos = _read_octets(response, pos)
        _, pos = _read_byte(response, pos)
        _, pos = _read_byte(response, pos)
        _, pos = _read_byte(response, pos)
        _, pos = _read_byte(response, pos)
        role_level, pos = _read_uint32(response, pos)
        role_culti, pos = _read_uint32(response, pos)
        _, pos = _read_uint32(response, pos)        # exp
        _, pos = _read_uint32(response, pos)        # sp
        _, pos = _read_uint32(response, pos)        # pp
        _, pos = _read_uint32(response, pos)        # hp
        _, pos = _read_uint32(response, pos)        # mp
        pos_x, pos = _read_float(response, pos)
        pos_y, pos = _read_float(response, pos)
        pos_z, pos = _read_float(response, pos)
        world_tag, pos = _read_uint32(response, pos)

        cls_idx = _cls2class(raw_cls)
        role_class = classes.get(cls_idx, f"Class{cls_idx}")

        role_path = ""
        if 19 < role_culti < 23:
            role_path = "Aware of Vacuity "
        elif 29 < role_culti < 33:
            role_path = "Aware of Principle "

        return {
            "role_class": role_class,
            "role_path": role_path,
            "role_level": role_level,
            "pos_x": round(pos_x, 1),
            "pos_y": round(pos_y, 1),
            "pos_z": round(pos_z, 1),
            "map": world_tag,
        }
    except Exception as e:
        logging.warning("get_role_base parse error for role %d: %s", role_id, e)
        return None
