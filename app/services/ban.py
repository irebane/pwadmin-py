"""
Sends a role/account ban packet to gdeliveryd — port of the Ban action in
account_tool.php (legacy pwAdmin). "Unban" is not a separate opcode; it's
done the same way the PHP app did it: re-issue a ban of the same type with
a near-zero duration so it overwrites and immediately expires the active one.
"""
from app.services.game_client import PacketWriter, _send_packet

_TIMEOUT = 5.0

# banType -> opcode, per packet_class.php
BAN_OPCODES = {
    1: 0x162,  # ban account
    2: 0x164,  # ban chat (account)
    3: 0x16A,  # ban chat (role)
    4: 0x168,  # ban role
}


async def send_ban(host: str, port: int, gm_id: int, target_id: int,
                    ban_type: int, duration: int, reason: str) -> tuple[bool, str]:
    opcode = BAN_OPCODES.get(ban_type)
    if not opcode:
        return False, "Invalid ban type."

    pw = PacketWriter()
    pw.write_uint32(gm_id)      # gmroleid, -1 = system
    pw.write_uint32(0)          # ssid
    pw.write_uint32(target_id)  # role/account id being banned
    pw.write_uint32(duration)   # seconds
    pw.write_ustring(reason)
    framed = pw.pack(opcode)

    data = await _send_packet(framed, host, port, timeout=_TIMEOUT)
    if data is None:
        return False, "Could not reach the game server to apply the ban."
    return True, ""
