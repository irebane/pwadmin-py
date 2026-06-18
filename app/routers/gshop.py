from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import get_db, require_admin
from app.services.gshop import parse_gshop_records, read_gshop, save_gshop
from app.models.game import GshopName
from app.services.items import get_item_name
from pydantic import BaseModel

router = APIRouter(prefix="/api/gshop")


@router.get("")
async def list_gshop(db: AsyncSession = Depends(get_db), user: dict = Depends(require_admin)):
    try:
        raw, count = await read_gshop()
        records = parse_gshop_records(raw)
    except (FileNotFoundError, ValueError):
        return {"count": 0, "items": []}
    names_result = await db.execute(select(GshopName))
    db_names = {n.item_id: n.item_name for n in names_result.scalars()}
    for r in records:
        r["item_name"] = db_names.get(r["item_id"]) or get_item_name(r["item_id"]) or ""
    return {"count": count, "items": records}


class GshopRecord(BaseModel):
    shop_id: int = 0
    main_cat: int = 0
    sub_cat: int = 0
    item_id: int
    qty: int = 1
    price: int = 0
    duration: int = 0
    class_mask: int = 0
    item_name: str = ""


@router.post("")
async def add_gshop_item(
    body: GshopRecord,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    raw, _ = await read_gshop()
    records = parse_gshop_records(raw)
    records.append(body.model_dump(exclude={"item_name"}))
    await save_gshop(records)
    if body.item_name:
        name_entry = GshopName(item_id=body.item_id, item_name=body.item_name)
        await db.merge(name_entry)
        await db.commit()
    return {"success": True, "count": len(records)}


@router.put("/{idx}")
async def update_gshop_item(
    idx: int,
    body: GshopRecord,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    raw, _ = await read_gshop()
    records = parse_gshop_records(raw)
    if idx >= len(records):
        raise HTTPException(404, "Record not found")
    records[idx] = body.model_dump(exclude={"item_name"})
    records[idx]["idx"] = idx
    await save_gshop(records)
    return {"success": True}


@router.delete("/{idx}")
async def delete_gshop_item(idx: int, user: dict = Depends(require_admin)):
    raw, _ = await read_gshop()
    records = parse_gshop_records(raw)
    if idx >= len(records):
        raise HTTPException(404)
    records.pop(idx)
    await save_gshop(records)
    return {"success": True, "count": len(records)}


@router.post("/save")
async def save_all_gshop(body: list[GshopRecord], user: dict = Depends(require_admin)):
    """Batch save — port of gshop_save.php."""
    records = [r.model_dump(exclude={"item_name"}) for r in body]
    await save_gshop(records)
    return {"success": True}
