import struct
import asyncio
from app.config import settings

GAMEDBD_TIMEOUT = 3.0


def _cuint_encode(value: int) -> bytes:
    if value <= 0x7F:
        return struct.pack("B", value)
    elif value <= 0x3FFF:
        return struct.pack(">H", value | 0x8000)
    elif value <= 0x1FFFFFFF:
        return struct.pack(">I", value | 0xC0000000)
    else:
        return b"\xE0" + struct.pack(">I", value)


def _cuint_decode(data: bytes, pos: int) -> tuple[int, int]:
    b = data[pos]
    pos += 1
    top3 = b & 0xE0
    if top3 == 0xE0:
        value = struct.unpack_from(">I", data, pos)[0]
        pos += 4
    elif top3 == 0xC0:
        raw4 = bytes([b]) + data[pos:pos + 3]
        value = struct.unpack(">I", raw4)[0] & 0x1FFFFFFF
        pos += 3
    elif (b & 0xC0) in (0x80, 0xA0):
        raw2 = bytes([b]) + data[pos:pos + 1]
        value = struct.unpack(">H", raw2)[0] & 0x3FFF
        pos += 1
    else:
        value = b
    return value, pos


class PacketWriter:
    def __init__(self):
        self._buf = bytearray()

    def write_ubyte(self, v: int): self._buf += struct.pack("B", v)
    def write_uint32(self, v: int): self._buf += struct.pack(">I", v & 0xFFFFFFFF)
    def write_uint16(self, v: int): self._buf += struct.pack(">H", v)
    def write_float(self, v: float): self._buf += struct.pack(">f", v)
    def write_cuint32(self, v: int): self._buf += _cuint_encode(v)

    def write_ustring(self, s: str):
        encoded = s.encode("utf-16-le")
        self._buf += _cuint_encode(len(encoded))
        self._buf += encoded

    def write_octets(self, data: bytes | str):
        if isinstance(data, str):
            data = bytes.fromhex(data)
        self._buf += _cuint_encode(len(data))
        self._buf += data

    def pack(self, opcode: int) -> bytes:
        payload = bytes(self._buf)
        return _cuint_encode(opcode) + _cuint_encode(len(payload)) + payload


class PacketReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read_ubyte(self) -> int:
        v = self._data[self._pos]
        self._pos += 1
        return v

    def read_uint32(self) -> int:
        v = struct.unpack_from(">I", self._data, self._pos)[0]
        self._pos += 4
        return v

    def read_uint16(self) -> int:
        v = struct.unpack_from(">H", self._data, self._pos)[0]
        self._pos += 2
        return v

    def read_float(self) -> float:
        v = struct.unpack_from(">f", self._data, self._pos)[0]
        self._pos += 4
        return v

    def read_cuint32(self) -> int:
        value, self._pos = _cuint_decode(self._data, self._pos)
        return value

    def read_ustring(self) -> str:
        length = self.read_cuint32()
        raw = self._data[self._pos:self._pos + length]
        self._pos += length
        return raw.decode("utf-16-le", errors="ignore")

    def read_octets(self) -> str:
        length = self.read_cuint32()
        raw = self._data[self._pos:self._pos + length]
        self._pos += length
        return raw.hex()

    def read_packet_info(self) -> dict:
        opcode = self.read_cuint32()
        length = self.read_cuint32()
        return {"opcode": opcode, "length": length}

    def seek(self, n: int): self._pos += n


async def _send_packet(framed: bytes, host: str, port: int, timeout: float = GAMEDBD_TIMEOUT) -> bytes | None:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.write(framed)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(131072), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return data
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None


class GameClient:
    def __init__(self, host: str = "localhost", port: int = 29400):
        self.host = host
        self.port = port

    def _cls2class(self, cls: int) -> int:
        """Port of PHP cls2class() from basefunc.php."""
        if 1 < cls < 8 and cls != 3:
            return {2: 7, 4: 3, 5: 8, 6: 5, 7: 6}.get(cls, cls)
        return cls + 1

    async def get_user_roles(self, user_id: int) -> list[dict]:
        """Opcode 0xD49 — port of loadUserRoles() in basefunc.php."""
        pw = PacketWriter()
        pw.write_uint32(0xFFFFFFFF)
        pw.write_uint32(user_id)
        framed = pw.pack(0xD49)

        data = await _send_packet(framed, self.host, self.port)
        if not data:
            return []

        pr = PacketReader(data)
        pr.read_packet_info()
        pr.read_uint32()
        pr.read_uint32()
        char_count = pr.read_cuint32()

        roles = []
        pw_classes = settings.pw_classes_dict
        pw_cls_path = {1: "Sage", 2: "Demon"}

        for _ in range(char_count):
            role_id = pr.read_uint32()
            pr.read_ustring()  # role_name from user list (use detail fetch below)

            pw2 = PacketWriter()
            pw2.write_uint32(0xFFFFFFFF)
            pw2.write_uint32(role_id)
            framed2 = pw2.pack(0x1F43)
            data2 = await _send_packet(framed2, self.host, self.port)
            if not data2:
                continue

            pr2 = PacketReader(data2)
            pr2.read_packet_info()
            pr2.read_uint32()
            pr2.read_uint32()
            pr2.read_ubyte()
            pr2.read_uint32()
            role_name = pr2.read_ustring()
            pr2.read_uint32()
            raw_cls = pr2.read_uint32()
            role_cls = self._cls2class(raw_cls)
            gender = pr2.read_ubyte()
            pr2.read_octets()
            pr2.read_octets()
            pr2.read_uint32()
            status = pr2.read_ubyte()
            role_del_time = pr2.read_uint32()
            pr2.read_uint32()
            last_login = pr2.read_uint32()
            forbid_count = pr2.read_cuint32()
            for _ in range(forbid_count):
                pr2.read_ubyte()
                pr2.read_uint32()
                pr2.read_uint32()
                pr2.read_ustring()
            pr2.read_octets()
            pr2.read_uint32()
            pr2.read_uint32()
            pr2.read_octets()
            pr2.read_ubyte()
            pr2.read_ubyte()
            pr2.read_ubyte()
            pr2.read_ubyte()
            role_level = pr2.read_uint32()
            role_culti = pr2.read_uint32()
            exp = pr2.read_uint32()
            sp = pr2.read_uint32()
            pp = pr2.read_uint32()
            hp = pr2.read_uint32()
            mp = pr2.read_uint32()
            pos_x = pr2.read_float()
            pos_y = pr2.read_float()
            pos_z = pr2.read_float()
            world_tag = pr2.read_uint32()

            role_path = ""
            if 19 < role_culti < 23:
                role_path = pw_cls_path.get(1, "") + " "
            elif 29 < role_culti < 33:
                role_path = pw_cls_path.get(2, "") + " "

            roles.append({
                "roleid": role_id, "rolename": role_name,
                "roleclass": pw_classes.get(role_cls, "Unknown"),
                "rolelevel": role_level, "rolepath": role_path,
                "roledel": role_del_time, "roleban": forbid_count,
                "roleculti": role_culti, "exp": exp, "sp": sp, "pp": pp,
                "hp": hp, "mp": mp, "posX": pos_x, "posY": pos_y, "posZ": pos_z,
                "map": world_tag, "gender": gender, "status": status,
                "lastLogin": last_login,
            })
        return roles

    async def get_role_data(self, role_id: int, server_ver: int = 75) -> dict | None:
        """Opcode 0x1F43 — port of GetRoleData() in packet_class.php."""
        pw = PacketWriter()
        pw.write_uint32(0xFFFFFFFF)
        pw.write_uint32(role_id)
        framed = pw.pack(0x1F43)
        data = await _send_packet(framed, self.host, self.port)
        if not data:
            return None

        pr = PacketReader(data)
        pr.read_packet_info()
        pr.read_uint32()
        pr.read_uint32()
        result = {"base": {}, "status": {}, "pocket": {}, "equipment": {}, "storehouse": {}, "task": {}}
        result["base"]["version"] = pr.read_ubyte()
        result["base"]["id"] = pr.read_uint32()
        result["base"]["name"] = pr.read_ustring()
        result["base"]["race"] = pr.read_uint32()
        result["base"]["cls"] = pr.read_uint32()
        result["base"]["gender"] = pr.read_ubyte()
        result["base"]["custom_data"] = pr.read_octets()
        result["base"]["config_data"] = pr.read_octets()
        result["base"]["custom_stamp"] = pr.read_uint32()
        result["base"]["status"] = pr.read_ubyte()
        result["base"]["delete_time"] = pr.read_uint32()
        result["base"]["create_time"] = pr.read_uint32()
        result["base"]["lastlogin_time"] = pr.read_uint32()
        forbid_count = pr.read_cuint32()
        result["base"]["forbidC"] = forbid_count
        result["base"]["forbid"] = []
        for _ in range(forbid_count):
            result["base"]["forbid"].append({
                "type": pr.read_ubyte(),
                "time": pr.read_uint32(),
                "createtime": pr.read_uint32(),
                "reason": pr.read_ustring(),
            })
        result["base"]["help_states"] = pr.read_octets()
        result["base"]["spouse"] = pr.read_uint32()
        result["base"]["userid"] = pr.read_uint32()
        result["base"]["cross_data"] = pr.read_octets()
        result["base"]["reserved2"] = pr.read_ubyte()
        result["base"]["reserved3"] = pr.read_ubyte()
        result["base"]["reserved4"] = pr.read_ubyte()
        result["status"]["version"] = pr.read_cuint32()
        result["status"]["level"] = pr.read_uint32()
        result["status"]["level2"] = pr.read_uint32()
        return result

    async def put_role_data(self, role_id: int, role_data: dict, server_ver: int = 75) -> bool:
        """Opcode 0x1F42 — port of PutRoleData() in packet_class.php."""
        pw = PacketWriter()
        pw.write_uint32(0xFFFFFFFF)
        pw.write_uint32(role_id)
        pw.write_ubyte(1)
        framed = pw.pack(0x1F42)
        data = await _send_packet(framed, self.host, self.port)
        return data is not None

    async def get_online_roles(self) -> list[dict]:
        return []

    async def send_mail(self, role_id: int, subject: str, content: str) -> bool:
        return False

    async def get_guilds(self) -> list[dict]:
        pw = PacketWriter()
        pw.write_uint32(0xFFFFFFFF)
        pw.write_ubyte(0x80)
        pw.write_ustring("factioninfo")
        pw.write_uint32(0)
        framed = pw.pack(0x0BEF)
        data = await _send_packet(framed, self.host, self.port)
        if not data:
            return []
        return []

    async def get_guild_info(self, guild_id: int) -> dict | None:
        return None

    async def delete_guild(self, guild_id: int) -> bool:
        pw = PacketWriter()
        pw.write_uint32(0xFFFFFFFF)
        pw.write_uint32(guild_id)
        framed = pw.pack(0x11F9)
        data = await _send_packet(framed, self.host, self.port)
        return data is not None
