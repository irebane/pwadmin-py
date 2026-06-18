import struct
import aiofiles
import os
from pathlib import Path
from app.config import settings

RECORD_SIZE = 148
HEADER_SIZE = 8
FIELDS_PER_RECORD = 37


def _gshop_path() -> Path:
    return Path(settings.server_path.rstrip("/")) / "gamed/config/gshopsev.data"


async def read_gshop() -> tuple[bytes, int]:
    """Returns (raw_bytes, count). Raises FileNotFoundError if missing."""
    path = _gshop_path()
    async with aiofiles.open(path, "rb") as f:
        raw = await f.read()
    if len(raw) < HEADER_SIZE:
        raise ValueError(f"gshopsev.data too small: {len(raw)} bytes")
    count = struct.unpack_from("<I", raw, 4)[0]
    return raw, count


def parse_gshop_records(raw: bytes) -> list[dict]:
    count = struct.unpack_from("<I", raw, 4)[0]
    records = []
    for i in range(count):
        offset = HEADER_SIZE + i * RECORD_SIZE
        if offset + RECORD_SIZE > len(raw):
            break
        f = struct.unpack_from("<37I", raw, offset)
        records.append({
            "idx": i,
            "shop_id": f[0],
            "main_cat": f[1],
            "sub_cat": f[2],
            "item_id": f[3],
            "qty": f[4],
            "price": f[5],
            "duration": f[7],
            "class_mask": f[9],
        })
    return records


def build_gshop_binary(header: bytes, records: list[dict]) -> bytes:
    """Rebuild the binary file from parsed records."""
    count = len(records)
    header_patched = header[:4] + struct.pack("<I", count) + header[8:]
    body = bytearray()
    for r in records:
        block = bytearray(RECORD_SIZE)
        vals = [
            r.get("shop_id", 0), r.get("main_cat", 0), r.get("sub_cat", 0),
            r.get("item_id", 0), r.get("qty", 1), r.get("price", 0),
            0, r.get("duration", 0), 0, r.get("class_mask", 0),
        ]
        for j, v in enumerate(vals):
            struct.pack_into("<I", block, j * 4, v)
        body += block
    return header_patched + bytes(body)


async def save_gshop(records: list[dict]) -> None:
    """Atomic write: write to .tmp then rename."""
    path = _gshop_path()
    raw, _ = await read_gshop()
    header = raw[:HEADER_SIZE]
    new_raw = build_gshop_binary(header, records)
    tmp = str(path) + ".tmp"
    async with aiofiles.open(tmp, "wb") as f:
        await f.write(new_raw)
    os.replace(tmp, str(path))
