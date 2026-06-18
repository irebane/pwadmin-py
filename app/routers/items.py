from fastapi import APIRouter, Depends, Query, HTTPException
from app.deps import require_admin
from app.services.items import get_item_name, search_items

router = APIRouter(prefix="/api/items")


@router.get("")
async def items_search(
    q: str = Query("", max_length=64),
    user: dict = Depends(require_admin),
):
    return search_items(q)


@router.get("/{item_id}")
async def item_by_id(item_id: int, user: dict = Depends(require_admin)):
    name = get_item_name(item_id)
    if name is None:
        raise HTTPException(404)
    return {"id": item_id, "name": name}
