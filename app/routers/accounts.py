from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db, get_current_user, require_admin
from app.services.accounts import (
    list_accounts, load_account, save_account,
    add_gold, set_gm_rank, delete_account,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/accounts")


@router.get("")
async def accounts_list(
    search: str = Query("", max_length=64),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    return await list_accounts(db, search, page, page_size)


@router.get("/{user_id}")
async def account_get(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user.get("is_admin") and user["id"] != user_id:
        raise HTTPException(403)
    return await load_account(db, user_id)


class SaveBody(BaseModel):
    current_password: str = ""
    new_password: str = ""
    email: str = ""
    truename: str = ""
    sex: int = 0
    birthday: str = ""


@router.post("/{user_id}/save")
async def account_save(
    user_id: int,
    body: SaveBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    error = await save_account(db, user, user_id, body.model_dump())
    if error:
        raise HTTPException(400, detail=error)
    return {"success": True}


class ToolBody(BaseModel):
    action: str
    value: int = 0


@router.post("/{user_id}/tool")
async def account_tool(
    user_id: int,
    body: ToolBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    if body.action == "add_gold":
        return {"success": await add_gold(db, user_id, body.value)}
    elif body.action == "set_gm":
        return {"success": await set_gm_rank(db, user_id, body.value)}
    elif body.action == "delete":
        return {"success": await delete_account(db, user_id)}
    raise HTTPException(400, detail=f"Unknown action: {body.action}")
