"""
Binary game mail sender — port of game_mail.php.
Connects to gdeliveryd on port 29100 and sends item mail via SysSendMail packet.
"""
import struct
import asyncio

_TIMEOUT = 5.0


def _varint(n: int) -> bytes:
    """PHP: if < 128 → pack("C"), else pack("n", n+32768)."""
    if n < 128:
        return struct.pack("B", n)
    return struct.pack(">H", n + 32768)


def _build_mail_packet(
    receiver: int, title: str, message: str,
    item_id: int, count: int, count_max: int,
    octets_hex: str, proctype: int, expire: int,
    guid1: int, guid2: int, mask: int, money: int,
) -> bytes:
    tID = b"\x00\x00\x01\x58"
    sys_id = b"\x00\x00\x00\x20"
    sys_type = b"\x03"

    title_b = title.encode("utf-16-le")
    msg_b = message.encode("utf-16-le")
    octets_b = bytes.fromhex(octets_hex) if octets_hex else b""

    body = (
        tID + sys_id + sys_type
        + struct.pack(">I", receiver & 0xFFFFFFFF)
        + _varint(len(title_b)) + title_b
        + _varint(len(msg_b)) + msg_b
        + struct.pack(">I", item_id & 0xFFFFFFFF)
        + b"\x00\x00\x00\x00"                    # pos
        + struct.pack(">I", count & 0xFFFFFFFF)
        + struct.pack(">I", count_max & 0xFFFFFFFF)
        + struct.pack(">H", len(octets_b) + 32768) + octets_b  # always 2-byte varint
        + struct.pack(">I", proctype & 0xFFFFFFFF)
        + struct.pack(">I", expire & 0xFFFFFFFF)
        + struct.pack(">I", guid1 & 0xFFFFFFFF)
        + struct.pack(">I", guid2 & 0xFFFFFFFF)
        + struct.pack(">I", mask & 0xFFFFFFFF)
        + struct.pack(">I", money & 0xFFFFFFFF)
    )

    return b"\x90\x76" + _varint(len(body)) + body


async def send_mail(
    host: str, port: int,
    receiver: int, title: str, message: str,
    item_id: int, count: int, count_max: int,
    octets_hex: str, proctype: int, expire: int,
    guid1: int, guid2: int, mask: int, money: int,
) -> tuple[bool, str]:
    """Send a game mail packet. Returns (success, error_message)."""
    pkt = _build_mail_packet(
        receiver, title, message, item_id, count, count_max,
        octets_hex, proctype, expire, guid1, guid2, mask, money,
    )
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=_TIMEOUT
        )
        writer.write(pkt)
        await writer.drain()
        await asyncio.wait_for(reader.read(8192), timeout=_TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return True, ""
    except asyncio.TimeoutError:
        return False, f"Timeout connecting to {host}:{port}"
    except (ConnectionRefusedError, OSError) as e:
        return False, str(e)
