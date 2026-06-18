import struct
import time as _time
import datetime as _dt
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.deps import require_admin
from app.services.items import get_item_name, search_items, _load_items
from app.services.item_data import get_template_data, build_item_opts
from app.services.game_client import GameClient, PacketWriter, _cuint_encode, _send_packet
from app.services.game_mail import send_mail
from app.config import settings

_PACKETS_FILE = Path("data/item_packets.txt")
_PACKETS_FILE.parent.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")
router = APIRouter()


# ── Page route ──────────────────────────────────────────────────────────────

@router.get("/item-builder")
async def item_builder_page(request: Request):
    items_data = _load_items()
    ctx = get_template_data(settings.server_ver)
    ctx["items_opts"] = build_item_opts(items_data, settings.server_ver)
    ctx["server_time"] = int(_time.time())
    ctx["tz_offset"] = int(_dt.datetime.now().astimezone().utcoffset().total_seconds())
    # Elf gear items grouped by category (grade field = slot 1-4)
    elf_raw = items_data.get("5", {}).get("14", {})
    elf_slots: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
    for entry in sorted(elf_raw.values(), key=lambda x: x.split("#")[0]):
        parts = entry.split("#")
        cat = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
        if cat in elf_slots:
            elf_slots[cat].append(entry)
    ctx["elf_gear_slots"] = elf_slots
    return templates.TemplateResponse(request, "item_builder/index.html", ctx)


# ── Item search (existing) ───────────────────────────────────────────────────

@router.get("/api/items")
async def items_search(
    q: str = Query("", max_length=64),
    user: dict = Depends(require_admin),
):
    return search_items(q)


@router.get("/api/items/{item_id}")
async def item_by_id(item_id: int, user: dict = Depends(require_admin)):
    name = get_item_name(item_id)
    if name is None:
        raise HTTPException(404)
    return {"id": item_id, "name": name}


# ── Character lookup ─────────────────────────────────────────────────────────

class CharLoadBody(BaseModel):
    rolename: str = ""


@router.post("/api/characters/load")
async def characters_load(body: CharLoadBody, user: dict = Depends(require_admin)):
    name = body.rolename.strip()
    if not name:
        return [{"error": "No name provided"}]

    pw = PacketWriter()
    pw.write_uint32(0xFFFFFFFF)
    pw.write_ustring(name)
    pw.write_ubyte(0)
    framed = pw.pack(3033)

    data = await _send_packet(framed, settings.lan_ip, settings.server_port)
    if data is None or len(data) < 15:
        return [{"error": "No response from game server", "success": "", "roleid": 0}]

    try:
        role_id = struct.unpack_from(">I", data, 11)[0]
        if role_id == 0xFFFFFFFF or role_id == 0:
            return [{"error": "Character not found", "success": "", "roleid": 0}]
        return [{"error": "", "success": "id found", "roleid": role_id}]
    except Exception:
        return [{"error": "Parse error", "success": "", "roleid": 0}]


# ── Item packet log ──────────────────────────────────────────────────────────

class ItemsLogBody(BaseModel):
    action: str
    itemlist: list[str] = []


@router.post("/api/items/log")
async def items_log(body: ItemsLogBody, user: dict = Depends(require_admin)):
    if body.action == "loadtempitems":
        if not _PACKETS_FILE.exists():
            return []
        lines = [ln.strip() for ln in _PACKETS_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return lines

    if body.action == "loadshopitems":
        from app.database import async_session
        from sqlalchemy import text
        try:
            async with async_session() as sess:
                rows = await sess.execute(text(
                    "SELECT itemid,itemname,itemoctet,itemmask,itemproctype,itemcount,itemmaxcount,"
                    "itemguid1,itemguid2,itemexpire FROM webshop LIMIT 200"
                ))
                result = []
                for r in rows:
                    line = (f"0#{r[0]}###{r[1]}##{r[0]}#{r[3]}#{r[4]}"
                            f"#{r[5]}#{r[6]}#{r[7]}#{r[8]}#{r[9]}#{r[2]}#####")
                    result.append(line)
                return result
        except Exception as e:
            return {"error": str(e)}

    raise HTTPException(400, detail="Invalid action")


# ── Item packet save ─────────────────────────────────────────────────────────

class ItemsSaveBody(BaseModel):
    action: str
    itemlist: list[str] = []


@router.post("/api/items/save")
async def items_save(body: ItemsSaveBody, user: dict = Depends(require_admin)):
    if body.action == "savetempitems":
        _PACKETS_FILE.parent.mkdir(exist_ok=True)
        content = "\n".join(body.itemlist)
        _PACKETS_FILE.write_text(content, encoding="utf-8")
        return {"success": f"{len(body.itemlist)} items saved"}
    raise HTTPException(400, detail="Invalid action")


# ── Send game packets ─────────────────────────────────────────────────────────

class PacketsBody(BaseModel):
    action: str
    itemlist: list[str] = []


@router.post("/api/game/packets")
async def game_packets(body: PacketsBody, user: dict = Depends(require_admin)):
    if body.action != "sendpacket":
        raise HTTPException(400, detail="Invalid action")

    results = []
    mail_port = 29100

    for item_str in body.itemlist:
        parts = item_str.split("#")
        if len(parts) < 16:
            results.append({"error": f"Malformed packet: too few fields ({len(parts)})"})
            continue
        try:
            receiver  = int(parts[0]) if parts[0] else 0
            money     = int(parts[1]) if parts[1] else 0
            title     = parts[2] or "Gift"
            message   = parts[3] or "A gift for you!"
            item_id   = int(parts[7]) if parts[7] else 0
            mask      = int(parts[8]) if parts[8] else 0
            proctype  = int(parts[9]) if parts[9] else 0
            count     = int(parts[10]) if parts[10] else 1
            max_count = int(parts[11]) if parts[11] else 1
            guid1     = int(parts[12]) if parts[12] else 0
            guid2     = int(parts[13]) if parts[13] else 0
            expire    = int(parts[14]) if parts[14] else 0
            octet     = parts[15] if len(parts) > 15 else ""
        except (ValueError, IndexError) as e:
            results.append({"error": f"Parse error: {e}"})
            continue

        if receiver <= 0:
            results.append({"error": "Invalid receiver ID"})
            continue

        ok, err = await send_mail(
            host=settings.lan_ip,
            port=mail_port,
            receiver=receiver,
            title=title,
            message=message,
            item_id=item_id,
            count=count,
            count_max=max_count,
            octets_hex=octet,
            proctype=proctype,
            expire=expire,
            guid1=guid1,
            guid2=guid2,
            mask=mask,
            money=money,
        )
        results.append({"success": True} if ok else {"error": err})

    return results
